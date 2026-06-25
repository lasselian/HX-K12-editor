"""USB HID usage codes and the device's media bitmap.

Values here were recovered by decompiling the OEM "MINI KeyBoard" (.NET) setting
software for the HX-K12 / Romoral macro pad (USB 1189:8840). Standard keys use
the normal USB HID Keyboard usage IDs (Usage Page 0x07); media keys use a small
*bitmap* that the firmware interprets when the key-type byte says "media".
See PROTOCOL.md for the full derivation.
"""

# --- Modifier byte bits (standard USB HID) -------------------------------
MODIFIERS = {
    "ctrl": 0x01, "lctrl": 0x01,
    "shift": 0x02, "lshift": 0x02,
    "alt": 0x04, "lalt": 0x04,
    "gui": 0x08, "win": 0x08, "lgui": 0x08, "super": 0x08,
    "rctrl": 0x10,
    "rshift": 0x20,
    "ralt": 0x40, "altgr": 0x40,
    "rgui": 0x80, "rwin": 0x80,
}

# --- Standard keyboard usage IDs (Usage Page 0x07) -----------------------
# A representative, easily-extended subset. Names are lower-case.
KEYS = {
    # letters
    **{chr(ord("a") + i): 0x04 + i for i in range(26)},
    # number row 1..9,0
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "enter": 0x28, "return": 0x28,
    "esc": 0x29, "escape": 0x29,
    "backspace": 0x2A, "bksp": 0x2A,
    "tab": 0x2B,
    "space": 0x2C,
    "minus": 0x2D, "equal": 0x2E,
    "lbracket": 0x2F, "rbracket": 0x30,
    "backslash": 0x31, "semicolon": 0x33, "quote": 0x34,
    "grave": 0x35, "comma": 0x36, "dot": 0x37, "period": 0x37, "slash": 0x38,
    "capslock": 0x39,
    **{f"f{i}": 0x3A + (i - 1) for i in range(1, 13)},   # f1..f12
    "printscreen": 0x46, "prtsc": 0x46,
    "scrolllock": 0x47, "pause": 0x48,
    "insert": 0x49, "home": 0x4A, "pageup": 0x4B,
    "delete": 0x4C, "del": 0x4C, "end": 0x4D, "pagedown": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
    "menu": 0x65,
}

# --- Media / consumer control --------------------------------------------
# Real 16-bit HID Consumer-page usage IDs. The firmware emits whatever value we
# store here verbatim as the consumer usage, so these must be the *real* codes
# (verified on hardware: writing 0xE2 makes the key mute the system).
MEDIA = {
    "mute": 0xE2,
    "volup": 0xE9, "volumeup": 0xE9, "vol+": 0xE9,
    "voldown": 0xEA, "volumedown": 0xEA, "vol-": 0xEA,
    "play": 0xCD, "playpause": 0xCD, "pause_media": 0xCD,
    "next": 0xB5, "nextsong": 0xB5,
    "prev": 0xB6, "prevsong": 0xB6, "previous": 0xB6,
    "stop": 0xB7,
}


def parse_combo(spec):
    """Parse 'ctrl+shift+a' -> (modifier_byte, keycode). Raises ValueError."""
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    mod = 0
    key = None
    for p in parts:
        if p in MODIFIERS:
            mod |= MODIFIERS[p]
        elif p in KEYS:
            if key is not None:
                raise ValueError(f"more than one non-modifier key in {spec!r}")
            key = KEYS[p]
        else:
            raise ValueError(f"unknown key token {p!r} in {spec!r}")
    if key is None:
        raise ValueError(f"no base key in {spec!r}")
    return mod, key
