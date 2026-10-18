from src.core.loaders.fabric import FabricLoader
from src.core.loaders.forge import ForgeLoader
from src.core.loaders.optifine import OptiFineLoader
from src.core.loaders.vanilla import VanillaLoader


class VersionManager:
    """
    Central Version and Loader Manager.
    Coordinates between Vanilla, Fabric, Forge, OptiFine and any future loaders.
    """

    def __init__(self, versions_dir: str):
        self.versions_dir = versions_dir
        self.vanilla = VanillaLoader()
        self.fabric = FabricLoader(vanilla_loader=self.vanilla)
        self.forge = ForgeLoader(vanilla_loader=self.vanilla)
        self.optifine = OptiFineLoader(vanilla_loader=self.vanilla)

        self.loaders = {
            "Vanilla": self.vanilla,
            "Fabric": self.fabric,
            "Forge": self.forge,
            "OptiFine": self.optifine,
        }

    def parse_version_string(self, version_str: str) -> tuple[str, str]:
        """
        Parses a UI version string like 'Fabric 1.20.1', 'Forge 1.20.1', or 'OptiFine 1.20.1'
        into (loader_name, mc_version).
        """
        cleaned = version_str.strip()
        if cleaned.startswith("Fabric "):
            return "Fabric", cleaned.replace("Fabric ", "").strip()
        elif cleaned.startswith("Forge "):
            return "Forge", cleaned.replace("Forge ", "").strip()
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

    def get_forge_supported_versions(self) -> list[str]:
        return self.forge.get_supported_versions()

    def get_required_java_major(self, mc_version: str, version_data: dict | None = None) -> int:
        """
        Determines the required Java major version (e.g. 8, 17, 21) based on
        version_data manifest or Minecraft release version rules.
        """
        if version_data:
            java_info = version_data.get("javaVersion", {})
            if isinstance(java_info, dict) and "majorVersion" in java_info:
                return java_info["majorVersion"]

        # Strip loader name prefix if passed raw
        _, clean_ver = self.parse_version_string(mc_version)

        try:
            parts = [int(x) for x in clean_ver.split(".") if x.isdigit()]
            if parts:
                major = parts[0]
                minor = parts[1] if len(parts) > 1 else 0
                patch = parts[2] if len(parts) > 2 else 0

                # Minecraft 1.20.5+, 1.21+, 26+ require Java 21
                if major >= 26 or (major == 1 and minor >= 21) or (major == 1 and minor == 20 and patch >= 5):
                    return 21
                # Minecraft 1.18 - 1.20.4 require Java 17
                elif major == 1 and minor >= 18 or major == 1 and minor == 17:
                    return 17
        except (ValueError, IndexError, TypeError):
            pass

        return 8

    def get_all_selectable_versions(self) -> list[str]:
        """
        Returns all valid launch configurations grouped per Minecraft release:
          - Vanilla (e.g. 1.20.1)
          - OptiFine (only if OptiFine exists for that version)
          - Fabric (only if Fabric officially supports that version)
          - Forge (only if Forge officially supports that version)
        """
        releases = self.vanilla.get_supported_versions()
        # Trigger background/cached fetch of supported versions
        self.fabric.fetch_supported_versions()
        self.optifine.fetch_available_versions()
        self.forge.fetch_supported_versions()

        combined_list = []
        for v in releases:
            combined_list.append(v)
            if self.optifine.is_supported(v):
                combined_list.append(f"OptiFine {v}")
            if self.fabric.is_supported(v):
                combined_list.append(f"Fabric {v}")
            if self.forge.is_supported(v):
                combined_list.append(f"Forge {v}")

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