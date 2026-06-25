"""Command-line front end for the HX-K12 editor.

Examples:
    python -m hxk12 info
    python -m hxk12 set-key 1 mute --dry-run
    python -m hxk12 set-key 1 mute
    python -m hxk12 set-key 5 "ctrl+c"
"""

import argparse
import sys

from . import protocol
from .device import Device, DeviceNotFound, find_hidraw
from .keycodes import MEDIA, parse_combo
from .protocol import KeyConfig, hexdump


def build_keyconfig(key_number, action, layer):
    """Turn a CLI action string into a KeyConfig."""
    a = action.strip().lower()
    if a in MEDIA:
        return KeyConfig(key_number=key_number, layer=layer, media=MEDIA[a])
    # otherwise treat as one or more '+'-combos separated by spaces/commas
    tokens = [t for t in a.replace(",", " ").split() if t]
    pairs = [parse_combo(tok) for tok in tokens]
    return KeyConfig(key_number=key_number, layer=layer, keystrokes=pairs)


def cmd_gui(args):
    from .gui.app import run
    return run()


def cmd_info(args):
    try:
        path = find_hidraw()
        print(f"Found HX-K12 vendor interface: {path}")
    except DeviceNotFound as e:
        print(e, file=sys.stderr)
        return 1
    print(f"VID:PID = {protocol.VID:04x}:{protocol.PID:04x}")
    return 0


def cmd_set_key(args):
    cfg = build_keyconfig(args.key, args.action, args.layer)
    report = cfg.encode_report()
    commit = protocol.flash_report()
    print(f"key {args.key}  layer {args.layer}  type={cfg.key_type:#04x}  action={args.action!r}")
    print(f"  program : {hexdump(report)}")
    print(f"  commit  : {hexdump(commit)}")
    if args.dry_run:
        print("(dry-run: nothing written)")
        return 0
    try:
        with Device() as dev:
            dev.program_key(cfg, commit=not args.no_commit)
    except (DeviceNotFound, PermissionError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print("written + committed to flash.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="hxk12", description="HX-K12 macro pad editor")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="detect the device").set_defaults(func=cmd_info)
    sub.add_parser("gui", help="launch the graphical editor").set_defaults(func=cmd_gui)

    sk = sub.add_parser("set-key", help="program one key/knob slot")
    sk.add_argument("key", type=int, help="key number (1..15) or knob slot")
    sk.add_argument("action", help="e.g. mute, vol+, 'ctrl+c', f13")
    sk.add_argument("--layer", type=int, default=1)
    sk.add_argument("--dry-run", action="store_true", help="print bytes, don't write")
    sk.add_argument("--no-commit", action="store_true", help="write but skip flash")
    sk.set_defaults(func=cmd_set_key)

    args = p.parse_args(argv)
    return args.func(args)
