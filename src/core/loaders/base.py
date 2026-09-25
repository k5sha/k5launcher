from abc import ABC, abstractmethod


class BaseLoader(ABC):
    """
    Abstract base class for all Minecraft version / loader providers.
    Each loader (Vanilla, Fabric, OptiFine, Forge, etc.) implements this interface.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_supported(self, mc_version: str) -> bool:
        """Checks if this loader supports the given Minecraft release version."""

    @abstractmethod
    def get_supported_versions(self) -> list[str]:
        """Returns a list of Minecraft versions supported by this loader."""

    @abstractmethod
    def prepare(
        self,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        loader_version: str | None = None,
        progress_callback=None,
    ) -> tuple[dict, list[str], str]:
        """
        Prepares and returns:
          1. version_data (dict): the complete version JSON data
          2. extra_args (list[str]): any extra command line arguments (e.g. tweakClass)
          3. version_label (str): version label for Minecraft --version arg
        """
