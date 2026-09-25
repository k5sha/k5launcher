import os

import pytest

from src.core.launcher import MyLauncherCore


@pytest.fixture
def launcher_core(tmp_path):
    return MyLauncherCore(root_dir=str(tmp_path))


def test_init_and_update_paths(tmp_path):
    """Test path initialization and automatic directory creation."""
    core = MyLauncherCore(root_dir=str(tmp_path / "custom_mc"))
    
    assert core.root_dir == os.path.abspath(str(tmp_path / "custom_mc"))
    assert os.path.exists(core.versions_dir)
    assert os.path.exists(core.libraries_dir)
    assert os.path.exists(core.runtimes_base_dir)


def test_update_root_dir(launcher_core, tmp_path):
    """Test updating root directory dynamically."""
    new_dir = tmp_path / "new_mc"
    launcher_core.update_root_dir(str(new_dir))
    
    assert launcher_core.root_dir == os.path.abspath(str(new_dir))
    assert os.path.exists(launcher_core.versions_dir)


def test_launch(launcher_core, mocker, tmp_path):
    """Test full launch command generation and process execution."""
    version_data = {
        "javaVersion": {"majorVersion": 21},
        "mainClass": "net.minecraft.client.main.Main",
        "assetIndex": {"id": "1.20"},
    }

    mocker.patch.object(
        launcher_core.version_manager, "parse_version_string", return_value=("Vanilla", "1.20.1")
    )
    mocker.patch.object(
        launcher_core.version_manager, "prepare_version", return_value=(version_data, [], "1.20.1")
    )
    mocker.patch.object(
        launcher_core.downloader, "download_client_and_libraries", return_value=[str(tmp_path / "client.jar")]
    )
    mocker.patch.object(launcher_core.downloader, "download_assets")

    mock_popen = mocker.patch("subprocess.Popen")
    mock_callback = mocker.MagicMock()

    java_file = tmp_path / "javaw.exe"
    java_file.write_text("fake binary")

    mocker.patch.object(
        launcher_core.java_manager, "detect_java_path", return_value=str(java_file)
    )
    mocker.patch.object(
        launcher_core.java_manager, "check_java_version", return_value=True
    )

    proc = launcher_core.launch(
        version="1.20.1",
        username="TestPlayer",
        java_path=str(java_file),
        ram_gb="4",
        progress_callback=mock_callback,
    )

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    command = args[0]

    assert command[0] == str(java_file)
    assert "-Xmx4G" in command
    assert "net.minecraft.client.main.Main" in command
    assert "--username" in command
    assert "TestPlayer" in command