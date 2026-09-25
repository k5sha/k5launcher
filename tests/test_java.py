import os
import zipfile

import pytest

from src.core.java import JavaManager


@pytest.fixture
def java_manager(tmp_path):
    runtimes_dir = tmp_path / "runtimes"
    root_dir = tmp_path
    runtimes_dir.mkdir()
    return JavaManager(str(runtimes_dir), str(root_dir))


def test_check_java_version_success(java_manager, mocker):
    """Test parsing subprocess output for a valid Java major version."""
    mock_proc = mocker.MagicMock()
    mock_proc.stderr = 'openjdk version "21.0.3" 2024-04-16'
    mock_proc.stdout = ""
    mocker.patch("subprocess.run", return_value=mock_proc)

    assert java_manager.check_java_version("javaw", 21) is True
    assert java_manager.check_java_version("javaw", 17) is False


def test_check_java_version_legacy_eight(java_manager, mocker):
    """Test parsing subprocess output for Java 8 (1.8.x versioning)."""
    mock_proc = mocker.MagicMock()
    mock_proc.stderr = 'java version "1.8.0_412"'
    mock_proc.stdout = ""
    mocker.patch("subprocess.run", return_value=mock_proc)

    assert java_manager.check_java_version("java", 8) is True


def test_download_portable_java(java_manager, mocker):
    """Test downloading and unpacking a portable OpenJDK distribution archive."""
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = b"fake zip content"
    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    def fake_copyfileobj(fsrc, fdst):
        with zipfile.ZipFile(fdst, "w") as z:
            z.writestr("jdk-21/bin/javaw.exe", b"fake executable content")

    mocker.patch("shutil.copyfileobj", side_effect=fake_copyfileobj)
    mocker.patch.object(java_manager, "check_java_version", return_value=True)

    exe_path = java_manager.download_portable_java(major_version=21)
    
    assert "java_21" in exe_path
    assert os.path.exists(exe_path)


def test_detect_java_path_local_runtime_exists(java_manager, tmp_path, mocker):
    """Test discovering pre-installed local runtime binary."""
    java_bin_dir = tmp_path / "runtimes" / "java_21" / "bin"
    java_bin_dir.mkdir(parents=True)
    java_exe = java_bin_dir / "javaw.exe"
    java_exe.write_text("fake binary")

    mocker.patch.object(java_manager, "check_java_version", return_value=True)

    found_path = java_manager.detect_java_path(required_major=21)
    assert found_path == str(java_exe)