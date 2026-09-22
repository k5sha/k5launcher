import json
import os
import urllib.request


class VersionManager:
    def __init__(self, versions_dir: str):
        self.versions_dir = versions_dir

    def get_release_versions(self) -> list:
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        try:
            req = urllib.request.Request(
                manifest_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                global_manifest = json.loads(response.read().decode())
            releases = [
                v["id"] for v in global_manifest["versions"] if v["type"] == "release"
            ]
            return releases
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return ["1.21.1", "1.20.1", "1.19.4", "1.16.5", "1.12.2", "1.8.9"]

    def get_fabric_loaders(self, game_version: str) -> list:
        loaders_url = f"https://meta.fabricmc.net/v2/versions/loader/{game_version}"
        try:
            req = urllib.request.Request(
                loaders_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                loaders = json.loads(resp.read().decode())
                return [
                    item["loader"]["version"] for item in loaders if "loader" in item
                ]
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return []

    def get_version_json(self, version: str) -> dict:
        version_json_path = os.path.join(self.versions_dir, version, f"{version}.json")
        if os.path.exists(version_json_path):
            with open(version_json_path, "r", encoding="utf-8") as f:
                return json.load(f)

        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        req = urllib.request.Request(
            manifest_url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req) as response:
            global_manifest = json.loads(response.read().decode())

        version_url = None
        for v in global_manifest["versions"]:
            if v["id"] == version:
                version_url = v["url"]
                break

        if not version_url:
            raise ValueError(f"Версія {version} не знайдена в маніфесті Mojang!")

        os.makedirs(os.path.dirname(version_json_path), exist_ok=True)
        urllib.request.urlretrieve(version_url, version_json_path)

        with open(version_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_fabric_version_json(
        self, game_version: str, loader_version: str | None = None
    ) -> dict:
        if not loader_version:
            loaders = self.get_fabric_loaders(game_version)
            if not loaders:
                raise ValueError(f"Fabric недоступний для версії {game_version}")
            loader_version = loaders[0]

        fabric_url = f"https://meta.fabricmc.net/v2/versions/loader/{game_version}/{loader_version}/profile/json"
        req = urllib.request.Request(fabric_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            fabric_data = json.loads(resp.read().decode())

        vanilla_data = self.get_version_json(game_version)

        merged_data = vanilla_data.copy()
        merged_data["mainClass"] = fabric_data["mainClass"]
        merged_data["libraries"] = fabric_data["libraries"] + vanilla_data["libraries"]

        return merged_data
