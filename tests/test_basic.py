"""Core tests: protocol byte-accuracy and config round-trip.

Run with:  python -m pytest   (or)  python -m unittest tests.test_basic
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hxk12 import config as config_mod
from hxk12.config import (Action, KIND_KEYS, KIND_MEDIA, KIND_NONE, Profile)
from hxk12.keycodes import parse_combo
from hxk12.layout import DEFAULT_LAYOUT
from hxk12.protocol import KeyConfig, flash_report


class TestProtocol(unittest.TestCase):
    def test_key1_mute_bytes(self):
        # verified on hardware: real mute consumer usage 0xE2 at offset 11
        cfg = KeyConfig(key_number=1, layer=1, media=0xE2)
        expected = bytes([0xFE, 0xFE, 0x01, 0x01, 0x02] + [0] * 6 + [0xE2, 0x00] + [0] * 52)
        self.assertEqual(cfg.encode_report(), expected)
        self.assertEqual(len(cfg.encode_report()), 65)

    def test_keyboard_combo_bytes(self):
        # ctrl+c -> count=1, modifier 0x01 @11, keycode 0x06 @12
        cfg = KeyConfig(key_number=5, layer=1, keystrokes=[(0x01, 0x06)])
        rep = cfg.encode_report()
        self.assertEqual(rep[0], 0xFE)        # report id / command
        self.assertEqual(rep[1], 0xFE)        # command marker
        self.assertEqual(rep[2], 5)           # key number
        self.assertEqual(rep[4], 0x01)        # type keyboard
        self.assertEqual(rep[10], 1)          # keystroke count
        self.assertEqual(rep[11], 0x01)       # modifier
        self.assertEqual(rep[12], 0x06)       # keycode

    def test_macro_bytes(self):
        # two keystrokes -> pairs at 11/12 and 13/14, count=2
        cfg = KeyConfig(key_number=6, keystrokes=[(0x01, 0x06), (0x01, 0x19)])
        rep = cfg.encode_report()
        self.assertEqual(rep[10], 2)
        self.assertEqual((rep[11], rep[12]), (0x01, 0x06))
        self.assertEqual((rep[13], rep[14]), (0x01, 0x19))

    def test_flash_commit(self):
        rep = flash_report()
        self.assertEqual(rep[:3], bytes([0x00, 0xAA, 0xAA]))
        self.assertEqual(len(rep), 65)


class TestConfig(unittest.TestCase):
    def test_action_to_keyconfig_parity(self):
        a = Action(kind=KIND_MEDIA, media="mute")
        cfg = a.to_keyconfig(1, 1)
        rep = cfg.encode_report()
        self.assertEqual(rep[:5].hex(), "fefe010102")   # cmd,cmd,key,layer,media-type
        self.assertEqual(rep[11], 0xE2)                  # real mute consumer usage

    def test_summaries(self):
        self.assertEqual(Action(kind=KIND_MEDIA, media="mute").summary(), "Mute")
        self.assertEqual(
            Action(kind=KIND_KEYS, sequence=["ctrl+c", "ctrl+v"]).summary(),
            "Ctrl+C → Ctrl+V")
        self.assertEqual(Action(kind=KIND_NONE).summary(), "")

    def test_validation(self):
        self.assertIsNone(Action(kind=KIND_KEYS, sequence=["ctrl+a"]).validate())
        self.assertIsNotNone(Action(kind=KIND_KEYS, sequence=["ctrl+nope"]).validate())
        self.assertIsNotNone(Action(kind=KIND_MEDIA, media="bogus").validate())

    def test_profile_roundtrip(self):
        p = Profile.blank(DEFAULT_LAYOUT, name="rt")
        p.layer(1).set(1, Action(kind=KIND_MEDIA, media="mute"))
        p.layer(2).set(5, Action(kind=KIND_KEYS, sequence=["ctrl+c", "ctrl+v"]))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            p.save(path)
            q = Profile.load(path)
        finally:
            os.unlink(path)
        self.assertEqual(q.layer(1).get(1).summary(), "Mute")
        self.assertEqual(q.layer(2).get(5).summary(), "Ctrl+C → Ctrl+V")
        self.assertEqual([ly.index for ly in q.layers], [1, 2, 3])

    def test_keyconfigs_for_layer_covers_all_slots(self):
        p = Profile.blank(DEFAULT_LAYOUT)
        cfgs = p.keyconfigs_for_layer(DEFAULT_LAYOUT, 1)
        self.assertEqual(len(cfgs), len(DEFAULT_LAYOUT.all_slots))


class TestKeycodes(unittest.TestCase):
    def test_literal_symbols(self):
        # '<' is the ISO 102nd key (0x64); ',' is the comma key (0x36)
        self.assertEqual(parse_combo("alt+<"), (0x04, 0x64))
        self.assertEqual(parse_combo("shift+<"), (0x02, 0x64))
        self.assertEqual(parse_combo("alt+,"), (0x04, 0x36))

    def test_nonus_aliases_agree(self):
        self.assertEqual(parse_combo("<"), parse_combo("nonusbackslash"))


class TestAutosave(unittest.TestCase):
    def test_roundtrip_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            old = os.environ.get("XDG_CONFIG_HOME")
            os.environ["XDG_CONFIG_HOME"] = d
            try:
                # nothing saved yet
                self.assertIsNone(config_mod.load_autosave())
                p = Profile.blank(DEFAULT_LAYOUT)
                p.layer(1).set(1, Action(kind=KIND_MEDIA, media="mute"))
                config_mod.autosave_profile(p)
                loaded = config_mod.load_autosave()
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.layer(1).get(1).summary(), "Mute")
            finally:
                if old is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = old

    def test_corrupt_file_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            old = os.environ.get("XDG_CONFIG_HOME")
            os.environ["XDG_CONFIG_HOME"] = d
            try:
                os.makedirs(os.path.join(d, "hxk12"))
                with open(config_mod.autosave_path(), "w") as f:
                    f.write("{ not valid json")
                self.assertIsNone(config_mod.load_autosave())
            finally:
                if old is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = old


if __name__ == "__main__":
    unittest.main()
