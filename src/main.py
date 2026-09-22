import sys

from PyQt6.QtWidgets import QApplication

from src.ui.app import K5LauncherApp


def main():
    app = QApplication(sys.argv)
    window = K5LauncherApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
