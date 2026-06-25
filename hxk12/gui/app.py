"""Application entry point for the GUI."""

import sys


def run(argv=None):
    from PyQt6.QtWidgets import QApplication

    from . import theme
    from .icons import setup_icon_theme
    from .main_window import MainWindow

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("HX-K12 Editor")
    app.setApplicationDisplayName("HX-K12 Editor")
    setup_icon_theme()
    theme.apply_font(app)

    win = MainWindow(app)
    app.setStyleSheet(theme.stylesheet(win.dark))
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
