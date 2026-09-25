from src.core.loaders.fabric import FabricLoader
from src.core.loaders.optifine import OptiFineLoader
from src.core.loaders.vanilla import VanillaLoader


class VersionManager:
    """
    Central Version and Loader Manager.
    Coordinates between Vanilla, Fabric, OptiFine and any future loaders.
    """

    def __init__(self, versions_dir: str):
        self.versions_dir = versions_dir
        self.vanilla = VanillaLoader()
        self.fabric = FabricLoader(vanilla_loader=self.vanilla)
        self.optifine = OptiFineLoader(vanilla_loader=self.vanilla)

        self.loaders = {
            "Vanilla": self.vanilla,
            "Fabric": self.fabric,
            "OptiFine": self.optifine,
        }

    def parse_version_string(self, version_str: str) -> tuple[str, str]:
        """
        Parses a UI version string like 'Fabric 1.20.1' or 'OptiFine 1.20.1'
        into (loader_name, mc_version).
        """
        cleaned = version_str.strip()
        if cleaned.startswith("Fabric "):
            return "Fabric", cleaned.replace("Fabric ", "").strip()
        elif cleaned.startswith("OptiFine "):
            return "OptiFine", cleaned.replace("OptiFine ", "").strip()
        else:
            return "Vanilla", cleaned

    def get_release_versions(self) -> list[str]:
        return self.vanilla.get_supported_versions()

    def get_optifine_supported_versions(self) -> list[str]:
        return self.optifine.get_supported_versions()

    def get_fabric_supported_versions(self) -> list[str]:
        return self.fabric.get_supported_versions()

    def get_all_selectable_versions(self) -> list[str]:
        """
        Returns all valid launch configurations grouped per Minecraft release:
          - Vanilla (e.g. 1.20.1)
          - OptiFine (only if OptiFine exists for that version)
          - Fabric (only if Fabric officially supports that version)
        """
        releases = self.vanilla.get_supported_versions()
        # Trigger background/cached fetch of supported versions
        self.fabric.fetch_supported_versions()
        self.optifine.fetch_available_versions()

        combined_list = []
        for v in releases:
            combined_list.append(v)
            if self.optifine.is_supported(v):
                combined_list.append(f"OptiFine {v}")
            if self.fabric.is_supported(v):
                combined_list.append(f"Fabric {v}")

        return combined_list

    def prepare_version(
        self,
        version_str: str,
        libraries_dir: str,
        loader_version: str | None = None,
        progress_callback=None,
    ) -> tuple[dict, list[str], str]:
        """
        Delegates version preparation to the appropriate loader provider.
        Returns: (version_data, extra_minecraft_args, version_label)
        """
        loader_name, mc_version = self.parse_version_string(version_str)
        loader = self.loaders.get(loader_name)
        if not loader:
            raise ValueError(f"Невідомий завантажувач: {loader_name}")

        return loader.prepare(
            mc_version=mc_version,
            versions_dir=self.versions_dir,
            libraries_dir=libraries_dir,
            loader_version=loader_version,
            progress_callback=progress_callback,
        )