"""Editable profile model + JSON persistence.

A :class:`Profile` holds one or more :class:`Layer`s; each layer maps a firmware
slot number to an :class:`Action`. Actions convert to ``protocol.KeyConfig`` for
flashing and to a short human label for the UI tiles.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import keycodes
from .layout import DEFAULT_LAYOUT, Layout
from .protocol import KeyConfig

# Curated media actions shown in the picker: (token, friendly label)
MEDIA_ACTIONS = [
    ("mute", "Mute"),
    ("volup", "Volume Up"),
    ("voldown", "Volume Down"),
    ("play", "Play / Pause"),
    ("prev", "Previous Track"),
    ("next", "Next Track"),
]

KIND_NONE = "none"
KIND_MEDIA = "media"
KIND_KEYS = "keys"

_MEDIA_GLYPHS = {
    "mute": "🔇", "volup": "🔊", "voldown": "🔉",
    "play": "⏯", "next": "⏭", "prev": "⏮", "stop": "⏹",
}


@dataclass
class Action:
    """What a single key/knob-action does."""
    kind: str = KIND_NONE
    media: str = ""                       # token from keycodes.MEDIA (kind=media)
    sequence: List[str] = field(default_factory=list)  # combo specs (kind=keys)

    # ---- conversions -----------------------------------------------------
    def is_empty(self) -> bool:
        return self.kind == KIND_NONE

    def validate(self) -> Optional[str]:
        """Return an error string, or None if valid."""
        if self.kind == KIND_MEDIA:
            if self.media not in keycodes.MEDIA:
                return f"unknown media action {self.media!r}"
        elif self.kind == KIND_KEYS:
            if not self.sequence:
                return "macro has no keystrokes"
            for spec in self.sequence:
                try:
                    keycodes.parse_combo(spec)
                except ValueError as e:
                    return str(e)
        return None

    def summary(self) -> str:
        """Short label for the UI tile."""
        if self.kind == KIND_MEDIA:
            label = dict(MEDIA_ACTIONS).get(self.media, self.media.title())
            return label
        if self.kind == KIND_KEYS:
            return " → ".join(_pretty_combo(s) for s in self.sequence)
        return ""

    def category(self) -> str:
        """'media' | 'keys' | 'none' — used for UI colour-coding."""
        if self.kind == KIND_MEDIA:
            return "media"
        if self.kind == KIND_KEYS:
            return "keys"
        return "none"

    def glyph(self) -> str:
        """A small emoji hinting at the action type."""
        if self.kind == KIND_MEDIA:
            return _MEDIA_GLYPHS.get(self.media, "🎵")
        if self.kind == KIND_KEYS:
            return "⚡" if len(self.sequence) > 1 else "⌨"
        return ""

    def to_keyconfig(self, slot: int, layer: int) -> KeyConfig:
        if self.kind == KIND_MEDIA:
            return KeyConfig(key_number=slot, layer=layer,
                             media=keycodes.MEDIA[self.media])
        if self.kind == KIND_KEYS:
            pairs = [keycodes.parse_combo(s) for s in self.sequence]
            return KeyConfig(key_number=slot, layer=layer, keystrokes=pairs)
        # empty -> a cleared key (type 0, all zero)
        return KeyConfig(key_number=slot, layer=layer)

    # ---- serialization ---------------------------------------------------
    def to_dict(self) -> dict:
        d = {"kind": self.kind}
        if self.kind == KIND_MEDIA:
            d["media"] = self.media
        elif self.kind == KIND_KEYS:
            d["sequence"] = list(self.sequence)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Action":
        kind = d.get("kind", KIND_NONE)
        return cls(kind=kind, media=d.get("media", ""),
                   sequence=list(d.get("sequence", [])))


def _pretty_combo(spec: str) -> str:
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    pretty = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "gui": "Super",
              "win": "Super", "super": "Super"}
    return "+".join(pretty.get(p.lower(), p.upper() if len(p) == 1 else p.title())
                    for p in parts)


@dataclass
class Layer:
    index: int                                   # 1-based firmware layer
    slots: Dict[int, Action] = field(default_factory=dict)

    def get(self, slot: int) -> Action:
        return self.slots.get(slot) or Action()

    def set(self, slot: int, action: Action):
        if action.is_empty():
            self.slots.pop(slot, None)
        else:
            self.slots[slot] = action


@dataclass
class Profile:
    name: str = "Untitled"
    layout_name: str = DEFAULT_LAYOUT.name
    layers: List[Layer] = field(default_factory=list)

    @classmethod
    def blank(cls, layout: Layout = DEFAULT_LAYOUT, name="Untitled") -> "Profile":
        return cls(name=name, layout_name=layout.name,
                   layers=[Layer(index=i + 1) for i in range(layout.layers)])

    def layer(self, index: int) -> Layer:
        for ly in self.layers:
            if ly.index == index:
                return ly
        ly = Layer(index=index)
        self.layers.append(ly)
        return ly

    def keyconfigs_for_layer(self, layout: Layout, index: int) -> List[KeyConfig]:
        """Every slot in the layout -> a KeyConfig (cleared if unassigned)."""
        ly = self.layer(index)
        cfgs = []
        for slot in layout.all_slots:
            cfgs.append(ly.get(slot).to_keyconfig(slot, index))
        return cfgs

    # ---- serialization ---------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "layout": self.layout_name,
            "version": 1,
            "layers": [
                {"index": ly.index,
                 "slots": {str(s): a.to_dict() for s, a in ly.slots.items()}}
                for ly in self.layers
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        layers = []
        for ld in d.get("layers", []):
            slots = {int(s): Action.from_dict(a)
                     for s, a in ld.get("slots", {}).items()}
            layers.append(Layer(index=int(ld["index"]), slots=slots))
        return cls(name=d.get("name", "Untitled"),
                   layout_name=d.get("layout", DEFAULT_LAYOUT.name),
                   layers=layers)

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Profile":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# --- "last layout" autosave ----------------------------------------------
# The pad has no read-back command, so the editor can't ask the device what it
# holds. Instead we mirror the in-editor layout to a file and reload it on the
# next launch, which is how the OEM tool effectively behaves too.

def _state_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or \
        os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "hxk12")


def autosave_path() -> str:
    return os.path.join(_state_dir(), "last.json")


def autosave_profile(profile: "Profile") -> None:
    """Quietly persist the current layout. Best-effort: never raises."""
    try:
        os.makedirs(_state_dir(), exist_ok=True)
        profile.save(autosave_path())
    except OSError:
        pass


def load_autosave() -> Optional["Profile"]:
    """Return the last autosaved profile, or None if missing/unreadable."""
    try:
        return Profile.load(autosave_path())
    except Exception:
        # Missing, corrupt, or from an incompatible version: start fresh.
        return None
