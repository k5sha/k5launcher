import json
import urllib.request

from src.core.loaders.base import BaseLoader
from src.core.loaders.vanilla import VanillaLoader


class FabricLoader(BaseLoader):
    META_GAMES_URL = "https://meta.fabricmc.net/v2/versions/game"
    META_LOADER_URL = "https://meta.fabricmc.net/v2/versions/loader"

    def __init__(self, vanilla_loader: VanillaLoader | None = None):
        super().__init__(name="Fabric")
        self.vanilla_loader = vanilla_loader or VanillaLoader()
        self._cached_supported_games = None

    def fetch_supported_versions(self) -> set[str]:
        """
        Fetches all Minecraft game versions that Fabric officially supports.
        Returns a set of version strings.
        """
        if self._cached_supported_games is not None:
            return self._cached_supported_games

        try:
            req = urllib.request.Request(
                self.META_GAMES_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                games_list = json.loads(response.read().decode())
                # Filter versions (releases and stable versions)
                supported = set()
                for item in games_list:
                    v = item.get("version")
                    if v:
                        supported.add(v)
                self._cached_supported_games = supported
                return self._cached_supported_games
        except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError):
            # Fallback list of well-known Fabric versions
            self._cached_supported_games = {
                "1.21.1",
                "1.21",
                "1.20.6",
                "1.20.4",
                "1.20.2",
                "1.20.1",
                "1.19.4",
                "1.19.2",
                "1.18.2",
                "1.17.1",
                "1.16.5",
                "1.15.2",
                "1.14.4",
            }
            return self._cached_supported_games

    def is_supported(self, mc_version: str) -> bool:
        """Checks whether Fabric supports the specified Minecraft version."""
        supported = self.fetch_supported_versions()
        return mc_version in supported

    def get_supported_versions(self) -> list[str]:
        return list(self.fetch_supported_versions())

    def get_fabric_loaders(self, game_version: str) -> list[str]:
        """Fetches available Fabric loader versions for the game version."""
        loaders_url = f"{self.META_LOADER_URL}/{game_version}"
        try:
            req = urllib.request.Request(
                loaders_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                loaders = json.loads(resp.read().decode())
                return [
                    item["loader"]["version"] for item in loaders if "loader" in item
                ]
        except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError):
            return []

    def prepare(
        self,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        loader_version: str | None = None,
        progress_callback=None,
    ) -> tuple[dict, list[str], str]:
        if not self.is_supported(mc_version):
            raise ValueError(f"Fabric офіційно недоступний для Minecraft {mc_version}!")

        if progress_callback:
            progress_callback(
                "Конфігурація Fabric", "Отримання Fabric профілю...", 0.03
            )

        if not loader_version:
            loaders = self.get_fabric_loaders(mc_version)
            if not loaders:
                raise ValueError(
                    f"Не знайдено сумісних Fabric loader для версії {mc_version}"
                )
            loader_version = loaders[0]

        fabric_url = (
            f"{self.META_LOADER_URL}/{mc_version}/{loader_version}/profile/json"
        )
        req = urllib.request.Request(fabric_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            fabric_data = json.loads(resp.read().decode())

        vanilla_data = self.vanilla_loader.get_version_json(mc_version, versions_dir)

        merged_data = vanilla_data.copy()
        merged_data["mainClass"] = fabric_data["mainClass"]
        merged_data["libraries"] = fabric_data["libraries"] + vanilla_data["libraries"]

        version_label = f"Fabric-{mc_version}"
        return merged_data, [], version_label
