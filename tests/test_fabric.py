import json
from urllib.error import URLError

import pytest

from src.core.loaders.fabric import FabricLoader


@pytest.fixture
def mock_vanilla(mocker):
    loader = mocker.MagicMock()
    loader.get_version_json.return_value = {
        "id": "1.20.1",
        "mainClass": "net.minecraft.client.main.Main",
        "libraries": [{"name": "vanilla:lib:1.0"}],
    }
    return loader


@pytest.fixture
def fabric_loader(mock_vanilla):
    return FabricLoader(vanilla_loader=mock_vanilla)


def test_fetch_supported_versions_success(fabric_loader, mocker):
    """Test successfully fetching supported game versions from Fabric API."""
    mock_data = [{"version": "1.20.1"}, {"version": "1.19.4"}]
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    versions = fabric_loader.fetch_supported_versions()
    assert "1.20.1" in versions
    assert "1.19.4" in versions


def test_fetch_supported_versions_fallback(fabric_loader, mocker):
    """Test returning fallback set of supported versions on network failure."""
    mocker.patch("urllib.request.urlopen", side_effect=URLError("Offline"))

    versions = fabric_loader.fetch_supported_versions()
    assert "1.20.1" in versions
    assert "1.16.5" in versions


def test_get_fabric_loaders_success(fabric_loader, mocker):
    """Test fetching available Fabric loader versions for a specific game version."""
    mock_loaders = [
        {"loader": {"version": "0.15.7"}},
        {"loader": {"version": "0.15.6"}},
    ]
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_loaders).encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    loaders = fabric_loader.get_fabric_loaders("1.20.1")
    assert loaders == ["0.15.7", "0.15.6"]


def test_prepare_unsupported_version(fabric_loader, mocker):
    """Test raising ValueError when attempting to prepare an unsupported game version."""
    mocker.patch.object(fabric_loader, "is_supported", return_value=False)

    with pytest.raises(ValueError, match="недоступний"):
        fabric_loader.prepare("1.0.0", "/tmp", "/tmp")


def test_prepare_success(fabric_loader, tmp_path, mocker):
    """Test merging Vanilla and Fabric JSON profiles correctly."""
    mocker.patch.object(fabric_loader, "is_supported", return_value=True)
    mocker.patch.object(
        fabric_loader, "get_fabric_loaders", return_value=["0.15.7"]
    )

    fabric_profile = {
        "mainClass": "net.fabricmc.loader.launch.knot.KnotClient",
        "libraries": [{"name": "net.fabricmc:fabric-loader:0.15.7"}],
    }

    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(fabric_profile).encode("utf-8")
    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    data, extra_args, label = fabric_loader.prepare(
        "1.20.1", str(tmp_path), str(tmp_path)
    )

    assert data["mainClass"] == "net.fabricmc.loader.launch.knot.KnotClient"
    assert len(data["libraries"]) == 2  # Fabric lib + Vanilla lib
    assert label == "Fabric-1.20.1"
    assert extra_args == []