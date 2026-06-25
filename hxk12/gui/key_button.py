"""Clickable key/slot tile widget."""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ..config import Action
from .icons import action_pixmap


class KeyTile(QFrame):
    """A card representing one firmware slot. Click to edit its action."""

    clicked = pyqtSignal(int)   # emits the slot number

    def __init__(self, slot: int, caption: str, compact: bool = False, parent=None):
        super().__init__(parent)
        self.slot = slot
        self.compact = compact
        self.setObjectName("tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(96 if not compact else 78, 78 if not compact else 60)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(3)

        self._caption = QLabel(caption)
        self._caption.setObjectName("tileSlot")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self._icon = QLabel()
        self._icon.setFixedSize(QSize(18, 18))
        self._icon.setVisible(False)
        self._summary = QLabel("—")
        self._summary.setObjectName("tileEmpty")
        self._summary.setWordWrap(True)
        self._summary.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._summary, 1)

        lay.addWidget(self._caption)
        lay.addLayout(row, 1)

        self._action = Action()
        self.set_action(self._action)

    def set_action(self, action: Action, icon_color=None):
        self._action = action
        if action.is_empty():
            self._summary.setText("—")
            self._summary.setObjectName("tileEmpty")
            self.setProperty("assigned", "false")
            self.setProperty("kind", "none")
            self._icon.setVisible(False)
        else:
            self._summary.setText(action.summary() or "—")
            self._summary.setObjectName("tileSummary")
            self.setProperty("assigned", "true")
            self.setProperty("kind", action.category())
            pm = action_pixmap(action, icon_color, 18) if icon_color is not None else None
            if pm is not None and not pm.isNull():
                self._icon.setPixmap(pm)
                self._icon.setVisible(True)
            else:
                self._icon.setVisible(False)
        for w in (self, self._summary):
            w.style().unpolish(w)
            w.style().polish(w)

    def action(self) -> Action:
        return self._action

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.slot)
        super().mousePressEvent(event)
