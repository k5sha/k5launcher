import pytest

from src.core.versions import VersionManager


@pytest.fixture
def version_manager(tmp_path):
    return VersionManager(str(tmp_path))


def test_parse_version_string(version_manager):
    """Test parsing UI version selection string into loader name and Minecraft release."""
    assert version_manager.parse_version_string("Fabric 1.20.1") == ("Fabric", "1.20.1")
    assert version_manager.parse_version_string("OptiFine 1.20.1") == ("OptiFine", "1.20.1")
    assert version_manager.parse_version_string("1.20.1") == ("Vanilla", "1.20.1")


def test_get_all_selectable_versions(version_manager, mocker):
    """Test building combined list of available game and loader versions."""
    mocker.patch.object(version_manager.vanilla, "get_supported_versions", return_value=["1.20.1"])
    mocker.patch.object(version_manager.optifine, "is_supported", return_value=True)
    mocker.patch.object(version_manager.fabric, "is_supported", return_value=True)
    mocker.patch.object(version_manager.optifine, "fetch_available_versions")
    mocker.patch.object(version_manager.fabric, "fetch_supported_versions")

    selectable = version_manager.get_all_selectable_versions()
    assert selectable == ["1.20.1", "OptiFine 1.20.1", "Fabric 1.20.1"]


def test_prepare_version_success(version_manager, mocker):
    """Test delegating version preparation to the appropriate loader."""
    mock_loader = mocker.MagicMock()
    mock_loader.prepare.return_value = ({"id": "1.20.1"}, [], "1.20.1")
    version_manager.loaders["Vanilla"] = mock_loader

    data, _, _ = version_manager.prepare_version("1.20.1", "/libraries")
    
    assert data == {"id": "1.20.1"}
    mock_loader.prepare.assert_called_once()


def test_prepare_version_invalid_loader(version_manager):
    """Test raising ValueError for an unrecognized loader type."""
    version_manager.loaders.clear()
    with pytest.raises(ValueError, match="Невідомий завантажувач"):
        version_manager.prepare_version("1.20.1", "/libraries")