import os
import sys

from src.utils.helpers import get_app_dir, resource_path


def test_resource_path_pyinstaller(monkeypatch, tmp_path):
    """Test resource path resolution when bundled with PyInstaller (_MEIPASS exists)."""
    fake_meipass = str(tmp_path / "meipass")
    monkeypatch.setattr(sys, "_MEIPASS", fake_meipass, raising=False)

    path = resource_path("assets/icon.png")
    assert path == os.path.join(fake_meipass, "assets/icon.png")


def test_resource_path_dev_mode(monkeypatch):
    """Test resource path resolution in standard development mode."""
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    path = resource_path("assets/icon.png")
    expected = os.path.join(os.path.abspath("."), "assets/icon.png")
    assert path == expected


def test_get_app_dir_frozen(monkeypatch, tmp_path):
    """Test application directory retrieval when running as a compiled binary (frozen)."""
    fake_exe = str(tmp_path / "bin" / "K5Launcher.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", fake_exe)

    app_dir = get_app_dir()
    assert app_dir == str(tmp_path / "bin")


def test_get_app_dir_dev_mode(monkeypatch):
    """Test application directory retrieval in development mode."""
    monkeypatch.delattr(sys, "frozen", raising=False)

    app_dir = get_app_dir()
    assert app_dir == os.path.abspath(".")