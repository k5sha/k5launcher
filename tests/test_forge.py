import json
import zipfile

import pytest

from src.core.loaders.forge import ForgeLoader


@pytest.fixture
def mock_vanilla(mocker):
    loader = mocker.MagicMock()
    loader.get_version_json.return_value = {
        "id": "1.7.10",
        "mainClass": "net.minecraft.client.main.Main",
        "libraries": [{"name": "vanilla:lib:1.0"}],
        "arguments": {
            "game": ["--username", "${auth_player_name}"],
            "jvm": ["-Djava.library.path=${natives_directory}"],
        },
    }
    return loader


@pytest.fixture
def forge_loader(mock_vanilla):
    return ForgeLoader(vanilla_loader=mock_vanilla)


def test_clean_mc_version(forge_loader):
    """Test sanitizing Minecraft version strings."""
    assert forge_loader._clean_mc_version("Forge 1.7.10") == "1.7.10"
    assert forge_loader._clean_mc_version("1.7.10") == "1.7.10"


def test_maven_to_path(forge_loader):
    """Test converting Maven coordinates to relative file system path."""
    maven_coords = "net.minecraftforge:forge:1.7.10-10.13.4.1614-1.7.10"
    expected = "net/minecraftforge/forge/1.7.10-10.13.4.1614-1.7.10/forge-1.7.10-10.13.4.1614-1.7.10.jar"
    assert forge_loader._maven_to_path(maven_coords) == expected

    maven_coords_classifier = "org.lwjgl:lwjgl:3.4.1:natives-windows"
    expected_classifier = "org/lwjgl/lwjgl/3.4.1/lwjgl-3.4.1-natives-windows.jar"
    assert forge_loader._maven_to_path(maven_coords_classifier) == expected_classifier


def test_fetch_promos_success(forge_loader, mocker):
    """Test fetching promotional releases manifest."""
    mock_promos = {
        "promos": {
            "1.7.10-recommended": "10.13.4.1614",
            "1.20.1-recommended": "47.2.0",
        }
    }
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_promos).encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    promos = forge_loader._fetch_promos()
    assert promos["1.7.10-recommended"] == "10.13.4.1614"
    assert forge_loader.is_supported("1.7.10") is True


def test_download_file_with_progress_fallback_candidate(forge_loader, mocker, tmp_path):
    """Test fallback to next candidate URL when first URL returns HTTP 404."""
    target_file = tmp_path / "installer.jar"

    mock_resp = mocker.MagicMock()
    mock_resp.read.side_effect = [b"downloaded_bytes", b""]
    mock_resp.headers.get.return_value = "16"

    def mock_urlopen(req, timeout=30):
        if "first-candidate" in req.full_url:
            from urllib.error import HTTPError
            raise HTTPError(req.full_url, 404, "Not Found", {}, None)
        ctx = mocker.MagicMock()
        ctx.__enter__.return_value = mock_resp
        return ctx

    mocker.patch("urllib.request.urlopen", side_effect=mock_urlopen)

    candidates = [
        "https://maven.minecraftforge.net/first-candidate.jar",
        "https://files.minecraftforge.net/second-candidate.jar",
    ]
    forge_loader.download_file_with_progress(candidates, str(target_file))

    assert target_file.exists()
    assert target_file.read_bytes() == b"downloaded_bytes"


def test_install_legacy_forge_extraction(forge_loader, tmp_path):
    """Test unpacking legacy Forge installer zip contents and universal JAR directly."""
    installer_jar = tmp_path / "forge-installer.jar"
    install_profile = {
        "install": {
            "target": "1.7.10-Forge10.13.4.1614-1.7.10",
            "filePath": "forge-1.7.10-10.13.4.1614-universal.jar",
            "path": "net.minecraftforge:forge:1.7.10-10.13.4.1614-1.7.10",
            "versionInfo": {
                "id": "1.7.10-Forge10.13.4.1614-1.7.10",
                "mainClass": "net.minecraft.launchwrapper.Launch",
                "libraries": [],
            },
        }
    }

    with zipfile.ZipFile(installer_jar, "w") as z:
        z.writestr("install_profile.json", json.dumps(install_profile))
        z.writestr("forge-1.7.10-10.13.4.1614-universal.jar", b"dummy_universaljar")
        z.writestr("maven/net/minecraftforge/forge/1.7.10/forge-1.7.10.jar", b"dummy_jar")

    versions_dir = tmp_path / "versions"
    res = forge_loader._install_legacy_forge(installer_jar, tmp_path, str(versions_dir))

    assert res is not None
    _, v_id = res
    assert v_id == "1.7.10-Forge10.13.4.1614-1.7.10"
    assert (versions_dir / v_id / f"{v_id}.json").exists()

    expected_forge_lib = (
        tmp_path / "libraries" / "net" / "minecraftforge" / "forge" / "1.7.10-10.13.4.1614-1.7.10" / "forge-1.7.10-10.13.4.1614-1.7.10.jar"
    )
    assert expected_forge_lib.exists()
    assert expected_forge_lib.read_bytes() == b"dummy_universaljar"


def test_prepare_missing_library_forces_reinstall(forge_loader, tmp_path, mocker):
    """Test re-triggering extraction if JSON profile exists but required forge library is missing on disk."""
    mocker.patch.object(forge_loader, "is_supported", return_value=True)
    mocker.patch.object(forge_loader, "get_official_build", return_value="10.13.4.1614")

    # Create cached JSON profile, but do NOT create the corresponding library on disk
    version_label = "Forge-1.7.10-10.13.4.1614"
    v_dir = tmp_path / "versions" / version_label
    v_dir.mkdir(parents=True)
    (v_dir / f"{version_label}.json").write_text(
        json.dumps({
            "id": version_label,
            "libraries": [{"name": "net.minecraftforge:forge:1.7.10-10.13.4.1614-1.7.10"}],
        }),
        encoding="utf-8",
    )

    # Mock download & legacy extraction to simulate fixing the missing library
    mocker.patch.object(forge_loader, "download_file_with_progress")
    mock_extraction_info = (
        {"id": version_label, "libraries": [{"name": "net.minecraftforge:forge:1.7.10-10.13.4.1614-1.7.10"}]},
        version_label,
    )
    mocker.patch.object(forge_loader, "_install_legacy_forge", return_value=mock_extraction_info)

    _, _, label = forge_loader.prepare(
        "1.7.10",
        str(tmp_path / "versions"),
        str(tmp_path / "libraries"),
        loader_version="10.13.4.1614",
    )

    # Verify _install_legacy_forge was called because forge library was missing on disk
    forge_loader._install_legacy_forge.assert_called_once()
    assert label == version_label


def test_prepare_unsupported_version(forge_loader, mocker):
    """Test raising ValueError for unsupported game version."""
    mocker.patch.object(forge_loader, "is_supported", return_value=False)

    with pytest.raises(ValueError, match="недоступний"):
        forge_loader.prepare("1.0.0", "/tmp", "/tmp")