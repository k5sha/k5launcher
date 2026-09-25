import json
import os
import urllib.request

from src.core.loaders.base import BaseLoader


class VanillaLoader(BaseLoader):
    MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    FALLBACK_RELEASES = ("1.21.1", "1.20.1", "1.19.4", "1.16.5", "1.12.2", "1.8.9")

    def __init__(self):
        super().__init__(name="Vanilla")
        self._cached_manifest = None
        self._cached_releases = None

    def _fetch_manifest(self) -> dict:
        if self._cached_manifest is not None:
            return self._cached_manifest
        try:
            req = urllib.request.Request(
                self.MANIFEST_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                self._cached_manifest = json.loads(response.read().decode())
                return self._cached_manifest
        except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError):
            return {
                "versions": [
                    {"id": v, "type": "release"} for v in self.FALLBACK_RELEASES
                ]
            }

    def get_supported_versions(self) -> list[str]:
        if self._cached_releases is not None:
            return self._cached_releases
        manifest = self._fetch_manifest()
        releases = [
            v["id"] for v in manifest.get("versions", []) if v.get("type") == "release"
        ]
        self._cached_releases = releases if releases else self.FALLBACK_RELEASES
        return self._cached_releases

    def is_supported(self, mc_version: str) -> bool:
        return mc_version in self.get_supported_versions()

    def get_version_json(self, mc_version: str, versions_dir: str) -> dict:
        version_json_path = os.path.join(versions_dir, mc_version, f"{mc_version}.json")
        if os.path.exists(version_json_path):
            with open(version_json_path, "r", encoding="utf-8") as f:
                return json.load(f)

        manifest = self._fetch_manifest()
        version_url = None
        for v in manifest.get("versions", []):
            if v["id"] == mc_version:
                version_url = v.get("url")
                break

        if not version_url:
            raise ValueError(f"Версія {mc_version} не знайдена в маніфесті Mojang!")

        os.makedirs(os.path.dirname(version_json_path), exist_ok=True)
        req = urllib.request.Request(version_url, headers={"User-Agent": "Mozilla/5.0"})
        with (
            urllib.request.urlopen(req, timeout=10) as resp,
            open(version_json_path, "wb") as f_out,
        ):
            f_out.write(resp.read())

        with open(version_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def prepare(
        self,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        loader_version: str | None = None,
        progress_callback=None,
    ) -> tuple[dict, list[str], str]:
        if progress_callback:
            progress_callback("Конфігурація Vanilla", f"Версія {mc_version}", 0.03)
        version_data = self.get_version_json(mc_version, versions_dir)
        return version_data, [], mc_version
