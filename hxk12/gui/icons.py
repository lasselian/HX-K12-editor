"""Theme-independent action icons.

Emoji glyphs render inconsistently (some systems lack the volume/mute ones), so
we use real icons from the desktop icon theme (Adwaita etc.), falling back to
Qt's built-in media icons. Each is tinted to a given colour so it stays crisp in
both light and dark themes.
"""

import os

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QStyle


def setup_icon_theme():
    """Ensure desktop icons resolve (some platforms don't set search paths)."""
    paths = QIcon.themeSearchPaths()
    for d in ("/usr/share/icons", "/usr/local/share/icons",
              os.path.expanduser("~/.local/share/icons"),
              os.path.expanduser("~/.icons")):
        if os.path.isdir(d) and d not in paths:
            paths.append(d)
    QIcon.setThemeSearchPaths(paths)
    if not QIcon.themeName():
        QIcon.setThemeName("Adwaita")
    QIcon.setFallbackThemeName("Adwaita")

_THEME_NAMES = {
    "mute": "audio-volume-muted-symbolic",
    "volup": "audio-volume-high-symbolic",
    "voldown": "audio-volume-low-symbolic",
    "play": "media-playback-start-symbolic",
    "prev": "media-skip-backward-symbolic",
    "next": "media-skip-forward-symbolic",
    "stop": "media-playback-stop-symbolic",
}
_SP = {
    "mute": QStyle.StandardPixmap.SP_MediaVolumeMuted,
    "volup": QStyle.StandardPixmap.SP_MediaVolume,
    "voldown": QStyle.StandardPixmap.SP_MediaVolume,
    "play": QStyle.StandardPixmap.SP_MediaPlay,
    "prev": QStyle.StandardPixmap.SP_MediaSkipBackward,
    "next": QStyle.StandardPixmap.SP_MediaSkipForward,
    "stop": QStyle.StandardPixmap.SP_MediaStop,
}
_KEYBOARD = "input-keyboard-symbolic"


def _base_icon(theme_name, sp):
    ic = QIcon.fromTheme(theme_name)
    if ic.isNull() and sp is not None:
        app = QApplication.instance()
        if app is not None:
            ic = app.style().standardIcon(sp)
    return ic


def _tint(icon: QIcon, size: int, color) -> QPixmap:
    pm = icon.pixmap(QSize(size, size))
    if pm.isNull():
        return pm
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return out


def media_icon(token, color, size=18) -> QIcon:
    return QIcon(_tint(_base_icon(_THEME_NAMES.get(token, ""), _SP.get(token)), size, color))


def action_pixmap(action, color, size=18) -> QPixmap:
    """Tinted pixmap for an Action, or a null pixmap for an empty action."""
    cat = action.category()
    if cat == "media":
        return _tint(_base_icon(_THEME_NAMES.get(action.media, ""),
                                _SP.get(action.media)), size, color)
    if cat == "keys":
        return _tint(_base_icon(_KEYBOARD, QStyle.StandardPixmap.SP_FileDialogDetailedView),
                     size, color)
    return QPixmap()
