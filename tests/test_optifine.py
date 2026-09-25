import json
import zipfile

import pytest

from src.core.loaders.optifine import OptiFineLoader


@pytest.fixture
def mock_vanilla(mocker):
    loader = mocker.MagicMock()
    loader.get_version_json.return_value = {
        "id": "1.20.1",
        "mainClass": "net.minecraft.client.main.Main",
        "minecraftArguments": "--username ${auth_player_name}",
        "libraries": [{"name": "vanilla:lib:1.0"}],
    }
    return loader


@pytest.fixture
def optifine_loader(mock_vanilla):
    return OptiFineLoader(vanilla_loader=mock_vanilla)


def test_fetch_available_versions_scrape(optifine_loader, mocker):
    """Test scraping available OptiFine versions from downloads webpage."""
    html_page = """
    <html>
        <a href="adloadx?f=OptiFine_1.20.1_HD_U_I1.jar">Download</a>
        <a href="adloadx?f=preview_OptiFine_1.21_HD_U_J1_pre1.jar">Download</a>
    </html>
    """
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = html_page.encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    version_map = optifine_loader.fetch_available_versions()
    assert "1.20.1" in version_map
    assert "OptiFine_1.20.1_HD_U_I1.jar" in version_map["1.20.1"]


def test_find_best_filename_prefers_stable(optifine_loader, mocker):
    """Test prioritizing stable releases over preview builds."""
    mock_map = {
        "1.20.1": [
            "preview_OptiFine_1.20.1_pre1.jar",
            "OptiFine_1.20.1_HD_U_I1.jar",
        ]
    }
    mocker.patch.object(
        optifine_loader, "fetch_available_versions", return_value=mock_map
    )

    best = optifine_loader.find_best_filename("1.20.1")
    assert best == "OptiFine_1.20.1_HD_U_I1.jar"


def test_resolve_download_url(optifine_loader, mocker):
    """Test extracting direct download link from the adloadx page HTML."""
    html_page = "<a href='downloadx?f=OptiFine_1.20.1_HD_U_I1.jar'>Mirror</a>"
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = html_page.encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    url = optifine_loader.resolve_download_url("OptiFine_1.20.1_HD_U_I1.jar")
    assert (
        url == "https://optifine.net/downloadx?f=OptiFine_1.20.1_HD_U_I1.jar"
    )


def test_install_from_jar(optifine_loader, tmp_path):
    """Test extracting OptiFine JAR archive and constructing valid version profile JSON."""
    jar_path = tmp_path / "OptiFine_1.20.1_HD_U_I1.jar"
    with zipfile.ZipFile(jar_path, "w") as z:
        z.writestr("launchwrapper-of.txt", "2.3")
        z.writestr("launchwrapper-of-2.3.jar", b"dummy launchwrapper bytes")

    versions_dir = tmp_path / "versions"
    libraries_dir = tmp_path / "libraries"

    version_id = optifine_loader.install_from_jar(
        str(jar_path), "1.20.1", str(versions_dir), str(libraries_dir)
    )

    assert version_id == "1.20.1-OptiFine_HD_U_I1"

    generated_json_path = (
        versions_dir / version_id / f"{version_id}.json"
    )
    assert generated_json_path.exists()

    with open(generated_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["mainClass"] == "net.minecraft.launchwrapper.Launch"
        assert (
            "--tweakClass optifine.OptiFineTweaker"
            in data["minecraftArguments"]
        )


def test_prepare(optifine_loader, tmp_path, mocker):
    """Test prepare method execution for OptiFineLoader."""
    expected_id = "1.20.1-OptiFine_HD_U_I1"
    mocker.patch.object(
        optifine_loader, "ensure_optifine_ready", return_value=expected_id
    )

    v_dir = tmp_path / "versions" / expected_id
    v_dir.mkdir(parents=True)
    v_json = v_dir / f"{expected_id}.json"
    v_json.write_text(json.dumps({"id": expected_id}), encoding="utf-8")

    data, extra_args, label = optifine_loader.prepare(
        "1.20.1", str(tmp_path / "versions"), str(tmp_path / "libraries")
    )

    assert data["id"] == expected_id
    assert extra_args == ["--tweakClass", "optifine.OptiFineTweaker"]
    assert label == "OptiFine-1.20.1"