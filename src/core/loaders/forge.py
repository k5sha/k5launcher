import json
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from src.core.loaders.base import BaseLoader
from src.core.loaders.vanilla import VanillaLoader


class ForgeLoader(BaseLoader):
    OFFICIAL_PROMOS_URL = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"

    def __init__(self, vanilla_loader: VanillaLoader | None = None):
        super().__init__(name="Forge")
        self.vanilla_loader = vanilla_loader or VanillaLoader()
        self._cached_promos: dict[str, str] | None = None

    def _clean_mc_version(self, mc_version: str) -> str:
        """Sanitizes the version string by stripping any leading loader prefix."""
        cleaned = mc_version.strip()
        if cleaned.startswith("Forge "):
            return cleaned.replace("Forge ", "").strip()
        return cleaned

    def _fetch_promos(self) -> dict[str, str]:
        """Fetch and cache the official promo build numbers from files.minecraftforge.net."""
        if self._cached_promos is not None:
            return self._cached_promos

        promos = {}
        try:
            req = urllib.request.Request(
                self.OFFICIAL_PROMOS_URL,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                promos = data.get("promos", {})
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            promos = {}

        self._cached_promos = promos
        return self._cached_promos

    def fetch_supported_versions(self) -> set[str]:
        """Extract all officially supported Minecraft versions from promo manifests."""
        promos = self._fetch_promos()
        supported = set()
        for key in promos:
            mc_version = key.split("-")[0]
            supported.add(mc_version)
        return supported

    def is_supported(self, mc_version: str) -> bool:
        """Check if Forge officially supports the given Minecraft version."""
        clean_version = self._clean_mc_version(mc_version)
        return clean_version in self.fetch_supported_versions()

    def get_supported_versions(self) -> list[str]:
        """Return a list of Minecraft versions supported by Forge."""
        return list(self.fetch_supported_versions())

    def get_official_build(self, mc_version: str) -> str | None:
        """Retrieve the recommended or latest Forge build version for a Minecraft version."""
        clean_version = self._clean_mc_version(mc_version)
        promos = self._fetch_promos()
        return promos.get(f"{clean_version}-recommended") or promos.get(f"{clean_version}-latest")

    def download_file_with_progress(
        self, urls: str | list[str], dest_path: str, progress_callback=None
    ):
        """Download file with fallback candidates and progress tracking for UI updates."""
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        candidate_urls = [urls] if isinstance(urls, str) else urls

        last_error = None
        for url in candidate_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    total_size = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    block_size = 64 * 1024

                    with open(dest_path, "wb") as f_out:
                        while True:
                            chunk = resp.read(block_size)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                pct = min(downloaded / total_size, 1.0)
                                progress_callback(
                                    "Завантаження Forge",
                                    f"{downloaded // 1024} KB / {total_size // 1024} KB",
                                    0.05 + pct * 0.35,
                                )
                return  # Successfully downloaded
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = e
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                continue

        if last_error:
            raise last_error

    def _merge_with_vanilla(self, forge_data: dict, mc_version: str, versions_dir: str) -> dict:
        """Merges Forge profile with base Vanilla profile to inherit all base libraries and arguments."""
        inherits_from = forge_data.get("inheritsFrom", mc_version)
        vanilla_data = self.vanilla_loader.get_version_json(inherits_from, versions_dir)

        merged_data = vanilla_data.copy()

        # Merge libraries
        merged_data["libraries"] = forge_data.get("libraries", []) + vanilla_data.get("libraries", [])

        # Merge arguments safely without overwriting vanilla flags
        vanilla_args = vanilla_data.get("arguments", {})
        forge_args = forge_data.get("arguments", {})

        merged_args = {}
        merged_args["game"] = vanilla_args.get("game", []) + forge_args.get("game", [])
        merged_args["jvm"] = forge_args.get("jvm", []) + vanilla_args.get("jvm", [])
        merged_data["arguments"] = merged_args

        # Copy non-conflicting metadata from Forge
        for key, val in forge_data.items():
            if key not in ("libraries", "arguments"):
                merged_data[key] = val

        return merged_data

    def _maven_to_path(self, maven_str: str) -> str:
        """Converts Maven coordinates (group:artifact:version[:classifier]) to a relative file path."""
        parts = maven_str.split(":")
        group = parts[0].replace(".", "/")
        artifact = parts[1]
        version = parts[2]
        classifier = f"-{parts[3]}" if len(parts) > 3 else ""
        return f"{group}/{artifact}/{version}/{artifact}-{version}{classifier}.jar"

    def _install_legacy_forge(
        self, installer_path: Path, game_root_dir: Path, versions_dir: str
    ) -> tuple[dict, str] | None:
        """Directly unpacks legacy Forge (1.7.10 - 1.12.2) manifests, bundled JARs, and libraries."""
        try:
            with zipfile.ZipFile(installer_path, "r") as z:
                if "install_profile.json" not in z.namelist():
                    return None

                data = json.loads(z.read("install_profile.json").decode("utf-8"))
                install_info = data.get("install", {})
                version_info = install_info.get("versionInfo") or data.get("versionInfo")

                if not version_info:
                    return None

                version_id = version_info.get("id", install_info.get("target"))
                if not version_id:
                    return None

                # Extract versionInfo JSON profile
                target_v_dir = Path(versions_dir) / version_id
                target_v_dir.mkdir(parents=True, exist_ok=True)
                v_json_path = target_v_dir / f"{version_id}.json"

                with open(v_json_path, "w", encoding="utf-8") as f:
                    json.dump(version_info, f, indent=2)

                libraries_dir = game_root_dir / "libraries"

                # Extract main Forge universal JAR defined in install["filePath"] to Maven path install["path"]
                file_path = install_info.get("filePath")
                maven_path_str = install_info.get("path")

                jar_member = None
                if file_path and file_path in z.namelist():
                    jar_member = file_path
                else:
                    for member in z.namelist():
                        m_lower = member.lower()
                        if (
                            m_lower.endswith(".jar")
                            and ("universal" in m_lower or "forge" in m_lower)
                            and not m_lower.endswith("-installer.jar")
                        ):
                            jar_member = member
                            break

                if jar_member and maven_path_str:
                    rel_target = self._maven_to_path(maven_path_str)
                    dest_file = libraries_dir / os.path.normpath(rel_target)
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(jar_member) as src, open(dest_file, "wb") as dst:
                        dst.write(src.read())

                # Unpack all bundled libraries inside maven/ or libraries/
                for member in z.namelist():
                    if member.startswith(("maven/", "libraries/")):
                        rel_path = member.replace("maven/", "", 1).replace("libraries/", "", 1)
                        if not rel_path or member.endswith("/"):
                            continue
                        dest_file = libraries_dir / os.path.normpath(rel_path)
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, open(dest_file, "wb") as dst:
                            dst.write(src.read())

                return version_info, version_id
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError):
            return None

    def prepare(
        self,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        loader_version: str | None = None,
        progress_callback=None,
        java_bin: str = "java",
    ) -> tuple[dict, list[str], str]:
        """
        Prepares Forge profile: downloads base vanilla JSON, creates launcher_profiles.json,
        runs installation (legacy extraction or modern installer), and merges manifests.
        """
        clean_version = self._clean_mc_version(mc_version)

        if not self.is_supported(clean_version):
            raise ValueError(f"Forge офіційно недоступний для Minecraft {clean_version}!")

        # 1. Ensure base vanilla version JSON exists
        self.vanilla_loader.get_version_json(clean_version, versions_dir)

        # 2. Determine target loader version
        if not loader_version:
            loader_version = self.get_official_build(clean_version)
            if not loader_version:
                raise ValueError(f"Не знайдено рекомендованої збірки Forge для версії {clean_version}")

        if loader_version.startswith(f"{clean_version}-"):
            full_version = loader_version
        else:
            full_version = f"{clean_version}-{loader_version}"

        version_label = f"Forge-{full_version}"

        candidate_versions = [full_version]
        if not full_version.endswith(f"-{clean_version}"):
            candidate_versions.append(f"{full_version}-{clean_version}")

        possible_json_paths = []
        for ver in candidate_versions:
            possible_json_paths.extend([
                Path(versions_dir) / version_label / f"{version_label}.json",
                Path(versions_dir) / ver / f"{ver}.json",
                Path(versions_dir) / f"{clean_version}-forge-{loader_version}" / f"{clean_version}-forge-{loader_version}.json",
                Path(versions_dir) / f"{clean_version}-Forge{loader_version}" / f"{clean_version}-Forge{loader_version}.json",
                Path(versions_dir) / f"{clean_version}-Forge{loader_version}-{clean_version}" / f"{clean_version}-Forge{loader_version}-{clean_version}.json",
            ])

        # 3. Return existing profile ONLY if Forge was installed AND required library file exists on disk
        for json_path in possible_json_paths:
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    forge_data = json.load(f)

                # Verify key Forge libraries exist in libraries directory
                libs = forge_data.get("libraries", [])
                forge_lib_missing = False
                for lib in libs:
                    lib_name = lib.get("name", "")
                    if "minecraftforge:forge" in lib_name or "cpw.mods:fml" in lib_name:
                        rel_p = self._maven_to_path(lib_name)
                        if not (Path(libraries_dir) / os.path.normpath(rel_p)).exists():
                            forge_lib_missing = True
                            break

                if not forge_lib_missing:
                    merged_data = self._merge_with_vanilla(forge_data, clean_version, versions_dir)
                    return merged_data, [], version_label

        # 4. Ensure launcher_profiles.json exists in target directory
        game_root_dir = Path(versions_dir).parent
        game_root_dir.mkdir(parents=True, exist_ok=True)
        profiles_json_path = game_root_dir / "launcher_profiles.json"
        if not profiles_json_path.exists():
            with open(profiles_json_path, "w", encoding="utf-8") as f:
                json.dump({"profiles": {}}, f, indent=2)

        # 5. Download Forge installer
        if progress_callback:
            progress_callback(
                "Конфігурація Forge",
                f"Завантаження офіційного інсталятора Forge {full_version}...",
                0.05,
            )

        candidate_urls = []
        for ver in candidate_versions:
            candidate_urls.extend([
                f"https://maven.minecraftforge.net/net/minecraftforge/forge/{ver}/forge-{ver}-installer.jar",
                f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{ver}/forge-{ver}-installer.jar",
            ])

        temp_dir = Path(libraries_dir) / "forge" / "temp"
        installer_path = temp_dir / f"forge-{full_version}-installer.jar"

        try:
            self.download_file_with_progress(
                candidate_urls, str(installer_path), progress_callback
            )

            # 6. Try legacy extraction first (for 1.7.10 - 1.12.2 SimpleInstaller)
            legacy_res = self._install_legacy_forge(installer_path, game_root_dir, versions_dir)
            if legacy_res:
                forge_data, extracted_id = legacy_res
                installer_path.unlink(missing_ok=True)
                merged_data = self._merge_with_vanilla(forge_data, clean_version, versions_dir)
                return merged_data, [], extracted_id

            # 7. Execute modern installer in headless mode for 1.13+
            if progress_callback:
                progress_callback(
                    "Установка Forge",
                    "Запуск офіційного інсталятора Forge...",
                    0.45,
                )

            cmd = [
                java_bin,
                "-jar",
                str(installer_path),
                "--installClient",
                str(game_root_dir),
            ]

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False,
            )

            installer_path.unlink(missing_ok=True)

            if process.returncode != 0:
                raise RuntimeError(f"Помилка під час установки Forge: {process.stdout}")

            for json_path in possible_json_paths:
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        forge_data = json.load(f)
                    merged_data = self._merge_with_vanilla(forge_data, clean_version, versions_dir)
                    return merged_data, [], version_label

            for folder in Path(versions_dir).iterdir():
                if folder.is_dir() and "forge" in folder.name.lower():
                    json_file = folder / f"{folder.name}.json"
                    if json_file.exists():
                        with open(json_file, "r", encoding="utf-8") as f:
                            forge_data = json.load(f)
                        merged_data = self._merge_with_vanilla(forge_data, clean_version, versions_dir)
                        return merged_data, [], version_label

            raise FileNotFoundError(
                f"Інсталятор завершив роботу, але файл профілю {version_label}.json не знайдено."
            )

        except Exception as e:  # noqa: BLE001
            if installer_path.exists():
                installer_path.unlink(missing_ok=True)
            raise RuntimeError(f"Помилка під час підготовки Forge: {e}")