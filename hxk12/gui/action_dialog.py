"""Dialog to assign an action (none / media / keyboard macro) to a slot.

Type is chosen with segmented buttons; media actions are a grid of buttons
(no dropdowns). Macros can be typed or recorded by pressing keys.
"""

from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QDialogButtonBox, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from .. import keycodes
from ..config import (Action, KIND_KEYS, KIND_MEDIA, KIND_NONE, MEDIA_ACTIONS)
from . import theme
from .icons import media_icon
from .keymap import event_to_spec

_TYPES = [("none", "None"), ("media", "Media key"), ("keys", "Keyboard / macro")]


class ActionDialog(QDialog):
    def __init__(self, caption: str, action: Action, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Assign — {caption}")
        self.setMinimumWidth(460)
        self._result = Action()
        self._recording = False
        self._media_buttons = {}        # token -> QPushButton
        dark = getattr(parent, "dark", None)
        if dark is None:
            dark = theme.system_prefers_dark()
        self._icon_color = theme.palette(dark)["text"]

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        # --- segmented type selector ---
        root.addWidget(_section("Action type"))
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        self.type_group = QButtonGroup(self)
        self.type_group.setExclusive(True)
        for idx, (_key, label) in enumerate(_TYPES):
            b = QPushButton(label)
            b.setObjectName("segment")
            b.setCheckable(True)
            self.type_group.addButton(b, idx)
            type_row.addWidget(b)
        root.addLayout(type_row)
        self.type_group.idClicked.connect(self.stack_set)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # page 0: none
        none_page = QWidget()
        npl = QVBoxLayout(none_page)
        npl.setContentsMargins(0, 4, 0, 0)
        npl.addWidget(QLabel("This key will be cleared — it won't send anything."))
        npl.addStretch(1)
        self.stack.addWidget(none_page)

        # page 1: media (grid of buttons)
        media_page = QWidget()
        mpl = QVBoxLayout(media_page)
        mpl.setContentsMargins(0, 0, 0, 0)
        mpl.setSpacing(8)
        mpl.addWidget(_section("Pick a media action"))
        grid = QGridLayout()
        grid.setSpacing(8)
        self._media_group = QButtonGroup(self)
        self._media_group.setExclusive(True)
        for i, (token, label) in enumerate(MEDIA_ACTIONS):
            b = QPushButton(f"  {label}")
            b.setObjectName("choice")
            b.setCheckable(True)
            b.setIcon(media_icon(token, self._icon_color))
            b.setIconSize(QSize(18, 18))
            self._media_group.addButton(b)
            self._media_buttons[token] = b
            grid.addWidget(b, i // 2, i % 2)
        mpl.addLayout(grid)
        mpl.addStretch(1)
        self.stack.addWidget(media_page)

        # page 2: keyboard / macro
        keys_page = QWidget()
        kp = QVBoxLayout(keys_page)
        kp.setContentsMargins(0, 0, 0, 0)
        kp.setSpacing(8)
        kp.addWidget(_section("Keystrokes (top to bottom)"))
        self.seq_list = QListWidget()
        kp.addWidget(self.seq_list)
        row = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("e.g.  ctrl+c   ·   f13   ·   shift+alt+t")
        self.entry.returnPressed.connect(self._add_entry)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_entry)
        rm_btn = QPushButton("Remove")
        rm_btn.setObjectName("flat")
        rm_btn.clicked.connect(self._remove_entry)
        row.addWidget(self.entry, 1)
        row.addWidget(add_btn)
        row.addWidget(rm_btn)
        kp.addLayout(row)
        rec_row = QHBoxLayout()
        self.record_btn = QPushButton("●  Record keystrokes")
        self.record_btn.setCheckable(True)
        self.record_btn.toggled.connect(self._toggle_record)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("flat")
        clear_btn.clicked.connect(self.seq_list.clear)
        rec_row.addWidget(self.record_btn)
        rec_row.addWidget(clear_btn)
        rec_row.addStretch(1)
        kp.addLayout(rec_row)
        self.error = QLabel("")
        self.error.setStyleSheet("color:#e5a50a; font-size:11px;")
        kp.addWidget(self.error)
        kp.addWidget(QLabel("Type a combo and Add, or click Record and press the "
                            "keys. Multiple lines = a macro sequence."))
        self.stack.addWidget(keys_page)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load(action)

    # ---- helpers ---------------------------------------------------------
    def stack_set(self, idx):
        self.stack.setCurrentIndex(idx)

    def _select_type(self, idx):
        self.type_group.button(idx).setChecked(True)
        self.stack.setCurrentIndex(idx)

    def _load(self, action: Action):
        # default media selection so there's always one ready
        if MEDIA_ACTIONS:
            self._media_buttons[MEDIA_ACTIONS[0][0]].setChecked(True)
        if action.kind == KIND_MEDIA:
            self._select_type(1)
            btn = self._media_buttons.get(action.media)
            if btn:
                btn.setChecked(True)
        elif action.kind == KIND_KEYS:
            self._select_type(2)
            for spec in action.sequence:
                self.seq_list.addItem(spec)
        else:
            self._select_type(0)

    def _add_entry(self):
        spec = self.entry.text().strip().lower()
        if not spec:
            return
        try:
            keycodes.parse_combo(spec)
        except ValueError as e:
            self.error.setText(str(e))
            return
        self.error.setText("")
        self.seq_list.addItem(spec)
        self.entry.clear()

    def _remove_entry(self):
        for item in self.seq_list.selectedItems():
            self.seq_list.takeItem(self.seq_list.row(item))

    def _selected_media(self):
        for token, btn in self._media_buttons.items():
            if btn.isChecked():
                return token
        return None

    # ---- live recording --------------------------------------------------
    def _toggle_record(self, on):
        if on:
            self._recording = True
            self.record_btn.setText("■  Stop recording")
            self.error.setText("Recording… press keys on your keyboard (Esc to stop).")
            QApplication.instance().installEventFilter(self)
        else:
            self._stop_record()

    def _stop_record(self):
        if not self._recording:
            return
        self._recording = False
        QApplication.instance().removeEventFilter(self)
        self.record_btn.setText("●  Record keystrokes")
        self.record_btn.setChecked(False)
        self.error.setText("")

    def eventFilter(self, obj, event):
        if self._recording and event.type() == QEvent.Type.KeyPress:
            if event.isAutoRepeat():
                return True
            if event.key() == Qt.Key.Key_Escape:
                self._stop_record()
                return True
            spec = event_to_spec(event)
            if spec:
                self.seq_list.addItem(spec)
            return True
        return super().eventFilter(obj, event)

    def reject(self):
        self._stop_record()
        super().reject()

    def _accept(self):
        self._stop_record()
        idx = self.type_group.checkedId()
        if idx == 1:
            token = self._selected_media()
            if not token:
                self.error.setText("Pick a media action.")
                return
            self._result = Action(kind=KIND_MEDIA, media=token)
        elif idx == 2:
            specs = [self.seq_list.item(i).text() for i in range(self.seq_list.count())]
            if not specs:
                self.error.setText("Add at least one keystroke (or pick None).")
                return
            self._result = Action(kind=KIND_KEYS, sequence=specs)
        else:
            self._result = Action(kind=KIND_NONE)
        self.accept()

    def result_action(self) -> Action:
        return self._result


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl
