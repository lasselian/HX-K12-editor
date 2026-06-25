"""Main application window: visual editor + flashing."""

import os

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from .. import config, device
from ..config import Profile
from ..layout import DEFAULT_LAYOUT
from . import theme
from .action_dialog import ActionDialog
from .key_button import KeyTile
from .knob_widget import KnobWidget


class FlashWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, configs):
        super().__init__()
        self.configs = configs

    def run(self):
        try:
            with device.Device() as dev:
                dev.flash_layout(self.configs)
            self.done.emit(True, "Layout flashed to the keyboard.")
        except PermissionError as e:
            self.done.emit(False, str(e))
        except (device.DeviceNotFound, device.DeviceError) as e:
            self.done.emit(False, str(e))
        except Exception as e:                      # pragma: no cover - safety net
            self.done.emit(False, f"Unexpected error: {e}")


class MainWindow(QMainWindow):
    def __init__(self, app, layout=DEFAULT_LAYOUT, dark=None):
        super().__init__()
        self.app = app
        self.layout_def = layout
        # Reopen with the last layout the user worked on; fall back to blank.
        saved = config.load_autosave()
        self.profile = saved if (saved and saved.layers) else Profile.blank(layout)
        self.current_layer = 1
        self.current_path = None
        self._theme_override = dark          # None = follow system
        self.dark = theme.system_prefers_dark() if dark is None else dark
        self._worker = None
        self._tiles = {}        # slot -> KeyTile (all, incl. knob sub-tiles)
        self._keytiles = []     # the 12 main key tiles (get shadows)
        self._knobcards = []    # knob cards (get shadows)
        self._header = None

        self.setWindowTitle("HX-K12 Editor")
        self.setMinimumSize(780, 640)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())
        outer.addWidget(self._build_body(), 1)

        self._populate_tiles()
        self.apply_theme(self.dark)
        self.app.styleHints().colorSchemeChanged.connect(self._on_system_scheme)
        self._watch_portal_theme()

        # Keep the connection pill live: poll so unplug/replug is reflected
        # without the user having to click it.
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(1000)
        self._status_timer.timeout.connect(self.refresh_status)
        self._status_timer.start()

    # ---- header ----------------------------------------------------------
    def _build_header(self):
        header = QFrame()
        header.setObjectName("header")
        self._header = header
        h = QHBoxLayout(header)
        h.setContentsMargins(18, 12, 14, 12)
        h.setSpacing(10)

        logo = QLabel("🎛")
        logo.setObjectName("logo")
        h.addWidget(logo)

        titlebox = QVBoxLayout()
        titlebox.setSpacing(0)
        title = QLabel("HX-K12 Editor")
        title.setObjectName("appTitle")
        sub = QLabel(self.layout_def.name)
        sub.setObjectName("appSubtitle")
        titlebox.addWidget(title)
        titlebox.addWidget(sub)
        h.addLayout(titlebox)

        h.addStretch(1)

        h.addWidget(QLabel("Layer"))
        self.layer_combo = QComboBox()
        for ly in self.profile.layers:
            self.layer_combo.addItem(f"Layer {ly.index}", ly.index)
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        h.addWidget(self.layer_combo)

        self.status_pill = QLabel("…")
        self.status_pill.setObjectName("pill")
        self.status_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_pill.mousePressEvent = lambda e: self.refresh_status()
        h.addWidget(self.status_pill)

        self.flash_btn = QPushButton("Flash to keyboard")
        self.flash_btn.setObjectName("accent")
        self.flash_btn.clicked.connect(self.on_flash)
        h.addWidget(self.flash_btn)

        menu_btn = QPushButton("⋯")
        menu_btn.setObjectName("flat")
        menu = QMenu(menu_btn)
        menu.addAction("New profile", self.on_new)
        menu.addAction("Open profile…", self.on_open)
        menu.addAction("Save profile…", self.on_save)
        menu.addSeparator()
        theme_menu = menu.addMenu("Theme")
        theme_menu.addAction("Follow system", lambda: self._set_theme(None))
        theme_menu.addAction("Light", lambda: self._set_theme(False))
        theme_menu.addAction("Dark", lambda: self._set_theme(True))
        menu.addSeparator()
        menu.addAction("About", self.on_about)
        menu_btn.setMenu(menu)
        h.addWidget(menu_btn)
        return header

    # ---- body ------------------------------------------------------------
    def _build_body(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("root")
        scroll.setWidget(content)

        v = QVBoxLayout(content)
        v.setContentsMargins(22, 20, 22, 22)
        v.setSpacing(18)

        v.addWidget(_label("Keys", "sectionTitle"))
        grid_host = QWidget()
        self.grid = QGridLayout(grid_host)
        self.grid.setSpacing(12)
        for key in self.layout_def.keys:
            tile = KeyTile(key.slot, f"Key {key.label}")
            tile.clicked.connect(self.on_tile_clicked)
            self.grid.addWidget(tile, key.row, key.col)
            self._register_tile(key.slot, tile)
            self._keytiles.append(tile)
        v.addWidget(grid_host)

        v.addWidget(_label("Knobs", "sectionTitle"))
        knob_row = QHBoxLayout()
        knob_row.setSpacing(12)
        for knob in self.layout_def.knobs:
            kw = KnobWidget(knob)
            kw.tileClicked.connect(self.on_tile_clicked)
            for slot in kw.slots():
                self._register_tile(slot, kw.tile(slot))
            knob_row.addWidget(kw)
            self._knobcards.append(kw)
        knob_row.addStretch(1)
        v.addLayout(knob_row)
        v.addStretch(1)
        return scroll

    def _register_tile(self, slot, tile):
        self._tiles[slot] = tile

    # ---- tile / layer logic ---------------------------------------------
    def _populate_tiles(self):
        color = theme.palette(self.dark)["text"]
        layer = self.profile.layer(self.current_layer)
        for slot, tile in self._tiles.items():
            tile.set_action(layer.get(slot), color)

    def on_tile_clicked(self, slot):
        layer = self.profile.layer(self.current_layer)
        caption = self._caption_for(slot)
        dlg = ActionDialog(caption, layer.get(slot), self)
        if dlg.exec():
            action = dlg.result_action()
            layer.set(slot, action)
            self._tiles[slot].set_action(layer.get(slot), theme.palette(self.dark)["text"])
            self._autosave()

    def _caption_for(self, slot):
        for k in self.layout_def.keys:
            if k.slot == slot:
                return f"Key {k.label}"
        for kn in self.layout_def.knobs:
            if slot == kn.left:
                return f"{kn.name} · turn left"
            if slot == kn.press:
                return f"{kn.name} · press"
            if slot == kn.right:
                return f"{kn.name} · turn right"
        return f"Slot {slot}"

    def _on_layer_changed(self, idx):
        self.current_layer = self.layer_combo.itemData(idx)
        self._populate_tiles()

    # ---- actions ---------------------------------------------------------
    def _autosave(self):
        """Mirror the current layout to disk so the next launch reopens with it."""
        config.autosave_profile(self.profile)

    def on_new(self):
        self.profile = Profile.blank(self.layout_def)
        self.current_path = None
        self._reload_layers()
        self._populate_tiles()
        self._autosave()

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open profile", os.path.expanduser("~"), "HX-K12 profile (*.json)")
        if not path:
            return
        try:
            self.profile = Profile.load(path)
        except Exception as e:
            QMessageBox.warning(self, "Open failed", str(e))
            return
        self.current_path = path
        self._reload_layers()
        self._populate_tiles()
        self._autosave()

    def on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save profile", self.current_path or
            os.path.join(os.path.expanduser("~"), "layout.json"),
            "HX-K12 profile (*.json)")
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        self.profile.name = os.path.splitext(os.path.basename(path))[0]
        try:
            self.profile.save(path)
        except Exception as e:
            QMessageBox.warning(self, "Save failed", str(e))
            return
        self.current_path = path
        self._autosave()
        self.statusBar().showMessage(f"Saved {path}", 4000)

    def _reload_layers(self):
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for ly in self.profile.layers:
            self.layer_combo.addItem(f"Layer {ly.index}", ly.index)
        self.layer_combo.blockSignals(False)
        self.current_layer = self.profile.layers[0].index if self.profile.layers else 1

    def on_flash(self):
        ok, _ = device.available()
        configs = self.profile.keyconfigs_for_layer(self.layout_def, self.current_layer)
        msg = (f"Flash Layer {self.current_layer} to the keyboard?\n\n"
               f"This writes all {len(configs)} slots of this layer to the "
               f"device's flash memory.")
        if QMessageBox.question(self, "Flash to keyboard", msg) != \
                QMessageBox.StandardButton.Yes:
            return
        self.flash_btn.setEnabled(False)
        self.flash_btn.setText("Flashing…")
        self._worker = FlashWorker(configs)
        self._worker.done.connect(self._on_flashed)
        self._worker.start()

    def _on_flashed(self, ok, message):
        self.flash_btn.setEnabled(True)
        self.flash_btn.setText("Flash to keyboard")
        if ok:
            self._autosave()
            self.statusBar().showMessage(message, 5000)
            QMessageBox.information(self, "Done", message)
        else:
            QMessageBox.warning(self, "Flash failed", message)
        self.refresh_status()

    def _set_theme(self, override):
        self._theme_override = override
        self.apply_theme(theme.system_prefers_dark() if override is None else override)

    def _on_system_scheme(self, *args):
        if self._theme_override is None:
            self.apply_theme(theme.system_prefers_dark())

    def _watch_portal_theme(self):
        """Live-follow GNOME/portal theme changes (Qt's signal doesn't fire there)."""
        try:
            from PyQt6.QtDBus import QDBusConnection
            QDBusConnection.sessionBus().connect(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Settings", "SettingChanged",
                self._on_portal_setting_changed)
        except Exception:
            pass

    def _on_portal_setting_changed(self, *args):
        if (len(args) >= 2 and args[0] == "org.freedesktop.appearance"
                and args[1] == "color-scheme" and self._theme_override is None):
            self.apply_theme(theme.system_prefers_dark())

    def on_about(self):
        QMessageBox.about(
            self, "HX-K12 Editor",
            "<b>HX-K12 Editor</b><br>"
            "Open, cross-platform macro-pad programmer.<br>"
            "Reverse-engineered from the OEM software.<br><br>"
            "Onboard macros are written to the keyboard's flash.")

    # ---- status / theme --------------------------------------------------
    def refresh_status(self):
        ok, info = device.available()
        p = theme.palette(self.dark)
        if ok:
            color, text = p["ok"], "Connected"
        else:
            color, text = p["warn"], "Not connected"
        self.status_pill.setText(text)
        self.status_pill.setToolTip(info)
        self.status_pill.setStyleSheet(
            f"background:{color}; color:white; border-radius:11px;"
            f"padding:4px 12px; font-weight:600;")

    def _apply_shadows(self):
        for tile in self._keytiles:
            theme.add_shadow(tile, self.dark, blur=18, dy=3)
        for card in self._knobcards:
            theme.add_shadow(card, self.dark, blur=22, dy=4)
        if self._header is not None:
            theme.add_shadow(self._header, self.dark, blur=16, dy=2, alpha=45)

    def apply_theme(self, dark: bool):
        self.dark = dark
        self.app.setStyleSheet(theme.stylesheet(dark))
        self._apply_shadows()
        self._populate_tiles()        # re-tint action icons for the new theme
        self.refresh_status()


def _label(text, obj):
    lbl = QLabel(text)
    lbl.setObjectName(obj)
    return lbl
