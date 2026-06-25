"""Map Qt key events to the HID key names used by hxk12.keycodes.

Used by the macro recorder so the user can press real keys instead of typing
combo specs. Returns names like 'a', 'f5', 'enter', and modifier names
'ctrl'/'shift'/'alt'/'gui' that keycodes.parse_combo() understands.
"""

from PyQt6.QtCore import Qt

_SPECIAL = {
    Qt.Key.Key_Return: 'enter', Qt.Key.Key_Enter: 'enter',
    Qt.Key.Key_Escape: 'esc', Qt.Key.Key_Backspace: 'backspace',
    Qt.Key.Key_Tab: 'tab', Qt.Key.Key_Space: 'space',
    Qt.Key.Key_Minus: 'minus', Qt.Key.Key_Equal: 'equal',
    Qt.Key.Key_BracketLeft: 'lbracket', Qt.Key.Key_BracketRight: 'rbracket',
    Qt.Key.Key_Backslash: 'backslash', Qt.Key.Key_Semicolon: 'semicolon',
    Qt.Key.Key_Apostrophe: 'quote', Qt.Key.Key_QuoteLeft: 'grave',
    Qt.Key.Key_Comma: 'comma', Qt.Key.Key_Period: 'dot', Qt.Key.Key_Slash: 'slash',
    Qt.Key.Key_CapsLock: 'capslock', Qt.Key.Key_Print: 'printscreen',
    Qt.Key.Key_ScrollLock: 'scrolllock', Qt.Key.Key_Pause: 'pause',
    Qt.Key.Key_Insert: 'insert', Qt.Key.Key_Home: 'home', Qt.Key.Key_PageUp: 'pageup',
    Qt.Key.Key_Delete: 'delete', Qt.Key.Key_End: 'end', Qt.Key.Key_PageDown: 'pagedown',
    Qt.Key.Key_Right: 'right', Qt.Key.Key_Left: 'left',
    Qt.Key.Key_Down: 'down', Qt.Key.Key_Up: 'up', Qt.Key.Key_Menu: 'menu',
}

# keys that are modifiers themselves — never recorded as a base key
MOD_KEYS = {
    Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
    Qt.Key.Key_AltGr, Qt.Key.Key_Super_L, Qt.Key.Key_Super_R,
}


def qt_key_name(key: int):
    """Qt key code -> HID key name, or None if unsupported."""
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return chr(ord('a') + (key - Qt.Key.Key_A))
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return chr(ord('0') + (key - Qt.Key.Key_0))
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        return f'f{key - Qt.Key.Key_F1 + 1}'
    return _SPECIAL.get(key)   # Qt.Key members compare/hash equal to their int


def modifier_names(mods) -> list:
    out = []
    if mods & Qt.KeyboardModifier.ControlModifier: out.append('ctrl')
    if mods & Qt.KeyboardModifier.ShiftModifier: out.append('shift')
    if mods & Qt.KeyboardModifier.AltModifier: out.append('alt')
    if mods & Qt.KeyboardModifier.MetaModifier: out.append('gui')
    return out


def event_to_spec(event):
    """QKeyEvent -> combo spec string like 'ctrl+c', or None to ignore."""
    key = event.key()
    if key in MOD_KEYS:
        return None
    name = qt_key_name(key)
    if not name:
        return None
    return '+'.join(modifier_names(event.modifiers()) + [name])
