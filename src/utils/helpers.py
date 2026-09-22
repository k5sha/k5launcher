import os
import sys

def resource_path(relative_path: str) -> str:
    """Отримує абсолютний шлях до ресурсу (працює і для PyInstaller, і для dev)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_app_dir() -> str:
    """Отримує директорію запуску додатка."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")