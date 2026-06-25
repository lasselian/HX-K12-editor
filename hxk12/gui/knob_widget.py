"""Knob card: three assignable sub-actions (turn-left / press / turn-right)."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel

from ..layout import KnobSlot
from .key_button import KeyTile


class KnobWidget(QFrame):
    tileClicked = pyqtSignal(int)   # forwards the slot number of the clicked sub-tile

    def __init__(self, knob: KnobSlot, parent=None):
        super().__init__(parent)
        self.knob = knob
        self.setObjectName("knob")

        grid = QGridLayout(self)
        grid.setContentsMargins(14, 12, 14, 14)
        grid.setSpacing(8)

        title = QLabel(knob.name)
        title.setObjectName("knobTitle")
        grid.addWidget(title, 0, 0, 1, 3)

        self.tiles = {}
        specs = [("⟲  Turn left", knob.left), ("⏺  Press", knob.press),
                 ("⟳  Turn right", knob.right)]
        for col, (cap, slot) in enumerate(specs):
            tile = KeyTile(slot, cap, compact=True)
            tile.clicked.connect(self.tileClicked.emit)
            self.tiles[slot] = tile
            grid.addWidget(tile, 1, col)

    def slots(self):
        return list(self.tiles.keys())

    def tile(self, slot) -> KeyTile:
        return self.tiles[slot]
