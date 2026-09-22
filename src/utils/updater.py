import json
import urllib.error
import urllib.request

CURRENT_VERSION = "v1.0.1"

def check_for_updates(current_version: str = CURRENT_VERSION):
    try:
        url = "https://api.github.com/repos/k5sha/k5launcher/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'K5Launcher'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            latest_version = data.get("tag_name")
            html_url = data.get("html_url", "https://github.com/k5sha/k5launcher/releases")
            if latest_version and latest_version != current_version:
                return latest_version, html_url
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        pass
    return None, None