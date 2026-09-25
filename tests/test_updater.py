import json
from urllib.error import URLError

from src.utils.updater import check_for_updates


def test_check_for_updates_new_version_available(mocker):
    """Test detecting a new release available on GitHub."""
    mock_data = {
        "tag_name": "v1.0.4",
        "html_url": "https://github.com/k5sha/k5launcher/releases/tag/v1.0.4",
    }
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    version, url = check_for_updates(current_version="v1.0.3")
    assert version == "v1.0.4"
    assert url == "https://github.com/k5sha/k5launcher/releases/tag/v1.0.4"


def test_check_for_updates_already_latest(mocker):
    """Test returning None when running the latest release."""
    mock_data = {
        "tag_name": "v1.0.3",
        "html_url": "https://github.com/k5sha/k5launcher/releases/tag/v1.0.3",
    }
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    version, url = check_for_updates(current_version="v1.0.3")
    assert version is None
    assert url is None


def test_check_for_updates_network_error(mocker):
    """Test handling network errors gracefully by returning None."""
    mocker.patch("urllib.request.urlopen", side_effect=URLError("Network error"))

    version, url = check_for_updates(current_version="v1.0.3")
    assert version is None
    assert url is None


def test_check_for_updates_invalid_json(mocker):
    """Test handling malformed JSON response gracefully."""
    mock_resp = mocker.MagicMock()
    mock_resp.read.return_value = b"invalid json content"

    mocker.patch(
        "urllib.request.urlopen",
        return_value=mocker.MagicMock(
            __enter__=mocker.MagicMock(return_value=mock_resp)
        ),
    )

    version, url = check_for_updates(current_version="v1.0.3")
    assert version is None
    assert url is None