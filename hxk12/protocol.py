"""Wire protocol for the HX-K12 / Romoral macro pad (USB 1189:8840).

Reverse-engineered from the OEM .NET app **and verified byte-for-byte against
real hardware** by programming keys and reading back what they emit. See
PROTOCOL.md.

A "program key" report is 65 bytes written to the vendor HID interface:

    [0]   0xFE     report-ID / command
    [1]   0xFE     command marker
    [2]   keynum   physical key (1..12) or knob-action slot (16..21)
    [3]   layer    1-based
    [4]   type     0x01 = keyboard, 0x02 = media/consumer
    [5..9] 0
    [10]  count    number of keystrokes (keyboard only)
    [11]  mod      keystroke-1 modifier   | OR consumer-usage low byte (media)
    [12]  key      keystroke-1 keycode    | OR consumer-usage high byte (media)
    [13]  mod      keystroke-2 modifier   (macros continue in pairs)
    [14]  key      keystroke-2 keycode
    ...

Then a flash-commit report persists it:

    [0] 0x00  [1] 0xAA  [2] 0xAA  rest 0
"""

from dataclasses import dataclass, field
from typing import List, Tuple

VID = 0x1189
PID = 0x8840
REPORT_LEN = 65            # report-id byte + 64 data bytes

CMD = 0xFE                 # program-key command (bytes 0 and 1)
COMMIT = (0x00, 0xAA, 0xAA)  # flash-commit report (byte0 is report-id 0)

# key-type byte (offset 4)
TYPE_KEYBOARD = 0x01
TYPE_MEDIA = 0x02

# offsets inside the report
OFF_KEYNUM = 2
OFF_LAYER = 3
OFF_TYPE = 4
OFF_COUNT = 10
OFF_FIRST = 11             # first (modifier, keycode) pair / consumer usage

# Knob action slots for this unit (New_Mul_Mouse=1): left / press / right
KNOB_SLOTS = {
    "k1": (16, 17, 18),
    "k2": (19, 20, 21),
}


@dataclass
class KeyConfig:
    """A single key/knob-action assignment."""
    key_number: int
    layer: int = 1
    # keyboard macro: list of (modifier_byte, keycode) pairs
    keystrokes: List[Tuple[int, int]] = field(default_factory=list)
    # media: a 16-bit HID consumer usage (e.g. 0xE2 = Mute). 0 = not media.
    media: int = 0

    @property
    def key_type(self) -> int:
        if self.media:
            return TYPE_MEDIA
        if self.keystrokes:
            return TYPE_KEYBOARD
        return 0

    def encode_report(self) -> bytes:
        """Build the 65-byte program-key report (verified against hardware)."""
        if self.media and self.keystrokes:
            raise ValueError("a key is either media or keyboard, not both")
        b = bytearray(REPORT_LEN)
        b[0] = CMD
        b[1] = CMD
        b[OFF_KEYNUM] = self.key_number & 0xFF
        b[OFF_LAYER] = self.layer & 0xFF
        b[OFF_TYPE] = self.key_type

        if self.media:
            b[OFF_FIRST] = self.media & 0xFF
            b[OFF_FIRST + 1] = (self.media >> 8) & 0xFF
        elif self.keystrokes:
            b[OFF_COUNT] = len(self.keystrokes)
            for i, (mod, code) in enumerate(self.keystrokes):
                off = OFF_FIRST + 2 * i
                if off + 1 >= REPORT_LEN:
                    raise ValueError("macro too long for one report")
                b[off] = mod & 0xFF
                b[off + 1] = code & 0xFF
        # empty action -> type 0, all zero (clears the key)
        return bytes(b)


def flash_report() -> bytes:
    b = bytearray(REPORT_LEN)
    b[0], b[1], b[2] = COMMIT
    return bytes(b)


def hexdump(data: bytes) -> str:
    return " ".join(f"{x:02x}" for x in data)
