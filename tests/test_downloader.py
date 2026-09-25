import json
import os
import zipfile

import pytest

from src.core.downloader import AssetDownloader


@pytest.fixture
def downloader(tmp_path):
    v_dir = tmp_path / "versions"
    l_dir = tmp_path / "libraries"
    n_dir = tmp_path / "natives"
    a_dir = tmp_path / "assets"
    for d in [v_dir, l_dir, n_dir, a_dir]:
        d.mkdir()
    return AssetDownloader(str(v_dir), str(l_dir), str(n_dir), str(a_dir))


def test_parse_maven_library(downloader):
    """Test parsing a Maven coordinate string into download URL and local path."""
    lib = {"name": "com.mojang:brigadier:1.0.18"}
    url, local_path = downloader._parse_maven_library(lib)
    
    assert url == "https://repo1.maven.org/maven2/com/mojang/brigadier/1.0.18/brigadier-1.0.18.jar"
    assert local_path.endswith(os.path.normpath("com/mojang/brigadier/1.0.18/brigadier-1.0.18.jar"))


def test_is_lib_allowed(downloader):
    """Test evaluating library installation rules for Windows OS."""
    lib_allowed = {"rules": [{"action": "allow", "os": {"name": "windows"}}]}
    lib_disallowed = {"rules": [{"action": "disallow", "os": {"name": "windows"}}]}
    lib_no_rules = {}

    assert downloader._is_lib_allowed(lib_allowed) is True
    assert downloader._is_lib_allowed(lib_disallowed) is False
    assert downloader._is_lib_allowed(lib_no_rules) is True


def test_extract_natives(downloader, tmp_path):
    """Test extracting native libraries (.dll) from a ZIP archive."""
    jar_path = tmp_path / "test_native.jar"
    with zipfile.ZipFile(jar_path, "w") as z:
        z.writestr("test.dll", b"fake_dll_data")
        z.writestr("META-INF/test.dll", b"ignored_meta_dll")

    downloader._extract_natives(str(jar_path))
    extracted_file = os.path.join(downloader.natives_dir, "test.dll")
    
    assert os.path.exists(extracted_file)
    with open(extracted_file, "rb") as f:
        assert f.read() == b"fake_dll_data"


def test_download_client_and_libraries(downloader, mocker):
    """Test downloading client JAR and resolving classpath libraries."""
    version_data = {
        "downloads": {"client": {"url": "https://example.com/client.jar"}},
        "libraries": [
            {
                "name": "org.lwjgl:lwjgl:3.3.1",
                "downloads": {
                    "artifact": {
                        "path": "org/lwjgl/lwjgl/3.3.1/lwjgl-3.3.1.jar",
                        "url": "https://example.com/lwjgl.jar",
                    }
                },
            }
        ],
    }

    mocker.patch.object(downloader, "_download_file")
    mock_callback = mocker.MagicMock()

    classpath = downloader.download_client_and_libraries(
        version_data, "1.20.1", progress_callback=mock_callback
    )

    assert len(classpath) == 2
    assert downloader._download_file.call_count >= 1
    mock_callback.assert_called()


def test_download_assets(downloader, mocker):
    """Test downloading and indexing asset files using multi-threading."""
    asset_index = {
        "objects": {
            "icons/icon.png": {"hash": "e00511894a4c5a31e8bb730a90e386eb4eefb743"}
        }
    }

    index_dir = os.path.join(downloader.assets_dir, "indexes")
    os.makedirs(index_dir, exist_ok=True)
    index_file = os.path.join(index_dir, "1.20.json")
    
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(asset_index, f)

    version_data = {
        "assetIndex": {
            "id": "1.20",
            "url": "https://example.com/1.20.json",
        }
    }

    mocker.patch("urllib.request.urlretrieve")
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = b"fake asset image content"
    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    downloader.download_assets(version_data)
    
    expected_asset_path = os.path.join(
        downloader.assets_dir,
        "objects",
        "e0",
        "e00511894a4c5a31e8bb730a90e386eb4eefb743",
    )
    assert os.path.exists(expected_asset_path)