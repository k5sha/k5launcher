import json
from urllib.error import URLError

import pytest

from src.core.loaders.vanilla import VanillaLoader


@pytest.fixture
def vanilla_loader():
    return VanillaLoader()


def test_fetch_manifest_success(vanilla_loader, mocker):
    """Test successful downloading of the Mojang version manifest."""
    mock_manifest = {"versions": [{"id": "1.20.1", "type": "release"}]}
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_manifest).encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    manifest = vanilla_loader._fetch_manifest()
    assert manifest == mock_manifest


def test_fetch_manifest_fallback(vanilla_loader, mocker):
    """Test falling back to default release list on network error."""
    mocker.patch("urllib.request.urlopen", side_effect=URLError("Network error"))

    manifest = vanilla_loader._fetch_manifest()
    assert "versions" in manifest
    assert (
        manifest["versions"][0]["id"] == vanilla_loader.FALLBACK_RELEASES[0]
    )


def test_get_supported_versions(vanilla_loader, mocker):
    """Test filtering release versions from the manifest."""
    mock_manifest = {
        "versions": [
            {"id": "1.20.1", "type": "release"},
            {"id": "23w12a", "type": "snapshot"},
        ]
    }
    mocker.patch.object(
        vanilla_loader, "_fetch_manifest", return_value=mock_manifest
    )

    supported = vanilla_loader.get_supported_versions()
    assert supported == ["1.20.1"]
    assert vanilla_loader.is_supported("1.20.1") is True
    assert vanilla_loader.is_supported("23w12a") is False


def test_get_version_json_existing_file(vanilla_loader, tmp_path):
    """Test reading an existing version JSON from the local filesystem."""
    versions_dir = tmp_path / "versions"
    version_dir = versions_dir / "1.20.1"
    version_dir.mkdir(parents=True)
    json_file = version_dir / "1.20.1.json"

    expected_data = {
        "id": "1.20.1",
        "mainClass": "net.minecraft.client.main.Main",
    }
    json_file.write_text(json.dumps(expected_data), encoding="utf-8")

    result = vanilla_loader.get_version_json("1.20.1", str(versions_dir))
    assert result == expected_data


def test_get_version_json_download_and_save(vanilla_loader, tmp_path, mocker):
    """Test downloading and saving version JSON when not present locally."""
    versions_dir = tmp_path / "versions"
    manifest_data = {
        "versions": [{"id": "1.20.1", "url": "https://example.com/1.20.1.json"}]
    }
    downloaded_data = {
        "id": "1.20.1",
        "mainClass": "net.minecraft.client.main.Main",
    }

    mocker.patch.object(
        vanilla_loader, "_fetch_manifest", return_value=manifest_data
    )

    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(downloaded_data).encode("utf-8")
    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    result = vanilla_loader.get_version_json("1.20.1", str(versions_dir))

    assert result == downloaded_data
    assert (versions_dir / "1.20.1" / "1.20.1.json").exists()


def test_get_version_json_not_found(vanilla_loader, tmp_path, mocker):
    """Test raising ValueError when requested version is missing in manifest."""
    mocker.patch.object(
        vanilla_loader, "_fetch_manifest", return_value={"versions": []}
    )

    with pytest.raises(ValueError, match="не знайдена в маніфесті"):
        vanilla_loader.get_version_json("9.9.9", str(tmp_path))


def test_prepare(vanilla_loader, tmp_path, mocker):
    """Test prepare method execution and progress callback invocation."""
    mocker.patch.object(
        vanilla_loader, "get_version_json", return_value={"id": "1.20.1"}
    )
    mock_callback = mocker.MagicMock()

    data, extra_args, label = vanilla_loader.prepare(
        "1.20.1",
        str(tmp_path),
        str(tmp_path),
        progress_callback=mock_callback,
    )

    assert data == {"id": "1.20.1"}
    assert extra_args == []
    assert label == "1.20.1"
    mock_callback.assert_called_once()