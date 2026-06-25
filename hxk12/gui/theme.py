"""Adwaita-inspired theming with a bit more flair.

Light/dark follows the system colour scheme (and live changes). Tiles are
colour-coded by action type, cards get soft shadows, and the accent button and
header use subtle gradients.
"""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QGuiApplication
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

LIGHT = {
    "window": "#f5f4f3",
    "card": "#ffffff",
    "card_alt": "#faf9f8",
    "header_top": "#ffffff",
    "header_bot": "#f3f1ef",
    "border": "#e2e0de",
    "text": "#1b1b1d",
    "dim": "#6a6862",
    "accent": "#3584e4",
    "accent2": "#2f74d0",
    "accent_text": "#ffffff",
    "hover": "rgba(0,0,0,0.05)",
    "active": "rgba(0,0,0,0.10)",
    "ok": "#2ec27e",
    "warn": "#e5a50a",
    "error": "#e01b24",
    "media": "#3584e4",
    "media_tint": "rgba(53,132,228,0.13)",
    "keys": "#9141ac",
    "keys_tint": "rgba(145,65,172,0.13)",
    "shadow": (0, 0, 0, 38),
}

DARK = {
    "window": "#1e1e20",
    "card": "#2b2b2e",
    "card_alt": "#323236",
    "header_top": "#323236",
    "header_bot": "#2a2a2d",
    "border": "#3a3a3e",
    "text": "#f3f3f4",
    "dim": "#a8a7a4",
    "accent": "#3584e4",
    "accent2": "#5a9bec",
    "accent_text": "#ffffff",
    "hover": "rgba(255,255,255,0.07)",
    "active": "rgba(255,255,255,0.12)",
    "ok": "#2ec27e",
    "warn": "#e5a50a",
    "error": "#ff6c6b",
    "media": "#62a0ea",
    "media_tint": "rgba(98,160,234,0.18)",
    "keys": "#c061cb",
    "keys_tint": "rgba(192,97,203,0.18)",
    "shadow": (0, 0, 0, 110),
}


def _portal_scheme():
    """'dark'/'light'/None from the xdg-desktop-portal appearance setting."""
    try:
        from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusVariant
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            return None
        iface = QDBusInterface(
            "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Settings", bus)
        reply = iface.call("Read", "org.freedesktop.appearance", "color-scheme")
        args = reply.arguments()
        if not args:
            return None
        v = args[0]
        while isinstance(v, QDBusVariant):
            v = v.variant()
        return {1: "dark", 2: "light"}.get(int(v))   # 0 = no preference
    except Exception:
        return None


def _gsettings_scheme():
    """'dark'/'light'/None from GNOME's color-scheme key."""
    try:
        import subprocess
        out = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True, text=True, timeout=1).stdout.lower()
        if "dark" in out:
            return "dark"
        if "light" in out or "default" in out:
            return "light"
    except Exception:
        pass
    return None


def system_prefers_dark() -> bool:
    """Best-effort system dark-mode detection.

    On Linux, Qt's colorScheme() is often Unknown, so we ask the desktop portal
    and GNOME settings first; Qt is the fallback (and the primary source on
    Windows/macOS, where it works well).
    """
    if sys.platform.startswith("linux"):
        for src in (_portal_scheme, _gsettings_scheme):
            s = src()
            if s in ("dark", "light"):
                return s == "dark"
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def palette(dark: bool) -> dict:
    return DARK if dark else LIGHT


def apply_font(app):
    f = app.font()
    if f.pointSize() < 10:
        f.setPointSize(10)
    app.setFont(f)


def add_shadow(widget, dark: bool, blur=24, dy=5, alpha=None):
    p = palette(dark)
    r, g, b, a = p["shadow"]
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(dy)
    eff.setColor(QColor(r, g, b, alpha if alpha is not None else a))
    widget.setGraphicsEffect(eff)


def stylesheet(dark: bool) -> str:
    p = palette(dark)
    return f"""
* {{ color: {p['text']}; outline: 0; }}
QWidget#root, QMainWindow {{ background: {p['window']}; }}
QDialog {{ background: {p['window']}; }}

/* ---- Header ---- */
QFrame#header {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {p['header_top']}, stop:1 {p['header_bot']});
    border-bottom: 1px solid {p['border']};
}}
QLabel#logo {{
    font-size: 20px; padding: 0 2px;
}}
QLabel#appTitle {{ font-size: 16px; font-weight: 800; letter-spacing: 0.2px; }}
QLabel#appSubtitle {{ color: {p['dim']}; font-size: 11px; }}

/* ---- Buttons ---- */
QPushButton {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 10px;
    padding: 7px 14px;
    color: {p['text']};
}}
QPushButton:hover {{ background: {p['hover']}; border-color: {p['accent']}; }}
QPushButton:pressed {{ background: {p['active']}; }}
QPushButton:disabled {{ color: {p['dim']}; }}

QPushButton#accent {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
               stop:0 {p['accent']}, stop:1 {p['accent2']});
    border: 1px solid {p['accent2']};
    color: {p['accent_text']};
    font-weight: 700;
    padding: 8px 18px;
}}
QPushButton#accent:hover {{ border: 1px solid {p['accent_text']}; }}
QPushButton#accent:disabled {{ background: {p['border']}; border-color: {p['border']}; color: {p['dim']}; }}

QPushButton#flat {{ border: none; background: transparent; padding: 7px 10px; }}
QPushButton#flat:hover {{ background: {p['hover']}; }}

QPushButton#segment {{
    border: 1px solid {p['border']}; border-radius: 9px;
    padding: 6px 14px; background: {p['card']}; color: {p['dim']}; font-weight: 600;
}}
QPushButton#segment:hover {{ border-color: {p['accent']}; }}
QPushButton#segment:checked {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
               stop:0 {p['accent']}, stop:1 {p['accent2']});
    color: {p['accent_text']}; border-color: {p['accent2']};
}}

QPushButton#choice {{
    text-align: left; padding: 11px 14px; border-radius: 12px;
    border: 1px solid {p['border']}; background: {p['card']};
    font-size: 13px; font-weight: 600;
}}
QPushButton#choice:hover {{ border-color: {p['media']}; }}
QPushButton#choice:checked {{
    background: {p['media_tint']}; border: 2px solid {p['media']}; color: {p['text']};
}}

/* ---- Tiles ---- */
QFrame#tile {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 16px;
}}
QFrame#tile:hover {{ border: 1px solid {p['accent']}; }}
QFrame#tile[assigned="true"][kind="media"] {{ border: 1px solid {p['media']}; background: {p['media_tint']}; }}
QFrame#tile[assigned="true"][kind="keys"]  {{ border: 1px solid {p['keys']};  background: {p['keys_tint']};  }}
QFrame#tile[assigned="true"][kind="media"]:hover {{ border: 2px solid {p['media']}; }}
QFrame#tile[assigned="true"][kind="keys"]:hover  {{ border: 2px solid {p['keys']};  }}
QLabel#tileSlot {{ color: {p['dim']}; font-size: 10px; font-weight: 700; letter-spacing: 0.4px; }}
QLabel#tileSummary {{ font-size: 13px; font-weight: 600; }}
QLabel#tileEmpty {{ color: {p['dim']}; font-size: 17px; font-weight: 600; }}

/* ---- Knob card ---- */
QFrame#knob {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
               stop:0 {p['card']}, stop:1 {p['card_alt']});
    border: 1px solid {p['border']};
    border-radius: 18px;
}}
QLabel#knobTitle {{ font-weight: 800; font-size: 13px; }}

/* ---- Status pill ---- */
QLabel#pill {{ border-radius: 12px; padding: 5px 13px; font-size: 12px; font-weight: 700; }}

/* ---- Inputs ---- */
QComboBox, QLineEdit {{
    background: {p['card']}; border: 1px solid {p['border']}; border-radius: 9px;
    padding: 6px 10px; min-height: 18px;
}}
QComboBox:hover, QLineEdit:hover, QComboBox:focus, QLineEdit:focus {{ border: 1px solid {p['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p['card']}; border: 1px solid {p['border']}; border-radius: 9px;
    selection-background-color: {p['accent']}; selection-color: {p['accent_text']}; padding: 4px;
}}
QListWidget {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 11px; padding: 4px; }}
QListWidget::item {{ padding: 6px 8px; border-radius: 7px; }}
QListWidget::item:selected {{ background: {p['accent']}; color: {p['accent_text']}; }}

QLabel#sectionTitle {{ color: {p['dim']}; font-size: 11px; font-weight: 800; letter-spacing: 1.2px; }}
QScrollArea {{ border: none; background: transparent; }}
QToolTip {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 7px; padding: 4px 8px; }}
"""
