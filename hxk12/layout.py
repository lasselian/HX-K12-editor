"""Physical layout descriptors for macro-pad variants.

Maps the visual editor to firmware *slot numbers* (the ``key number`` byte).
Slot numbers were recovered from the OEM app (see PROTOCOL.md):

* physical keys 1..N  -> slots 1..N
* knobs (this unit, New_Mul_Mouse=1): K1 left/press/right = 16/17/18,
  K2 = 19/20/21.

The model is data-driven so other variants (more/less keys or knobs) can be
added without touching the UI.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class KeySlot:
    slot: int           # firmware key number
    label: str          # default display label, e.g. "1"
    row: int
    col: int


@dataclass(frozen=True)
class KnobSlot:
    name: str           # e.g. "Knob 1"
    left: int           # slot for turn-left
    press: int          # slot for press
    right: int          # slot for turn-right


@dataclass(frozen=True)
class Layout:
    name: str
    cols: int
    keys: List[KeySlot]
    knobs: List[KnobSlot]
    layers: int = 3

    @property
    def all_slots(self):
        slots = [k.slot for k in self.keys]
        for kn in self.knobs:
            slots += [kn.left, kn.press, kn.right]
        return slots


def _grid(n, cols):
    return [(i // cols, i % cols) for i in range(n)]


# This user's unit: 12 keys (4x3) + 2 knobs.
HX_K12 = Layout(
    name="HX-K12 (12 keys + 2 knobs)",
    cols=4,
    keys=[
        KeySlot(slot=i + 1, label=str(i + 1), row=r, col=c)
        for i, (r, c) in enumerate(_grid(12, 4))
    ],
    knobs=[
        KnobSlot("Knob 1", left=16, press=17, right=18),
        KnobSlot("Knob 2", left=19, press=20, right=21),
    ],
    layers=3,
)

DEFAULT_LAYOUT = HX_K12
