import os
import sys


def resource_path(relative_path: str) -> str:
    """Gets the absolute path to a resource (works for both PyInstaller and dev mode)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_app_dir() -> str:
    """Gets the application execution directory."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")