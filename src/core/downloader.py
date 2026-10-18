import json
import os
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor


class AssetDownloader:
    MAVEN_REPOS = [
        "https://libraries.minecraft.net/",
        "https://repo1.maven.org/maven2/",
        "https://maven.minecraftforge.net/",
    ]

    def __init__(
        self, versions_dir: str, libraries_dir: str, natives_dir: str, assets_dir: str
    ):
        self.versions_dir = versions_dir
        self.libraries_dir = libraries_dir
        self.natives_dir = natives_dir
        self.assets_dir = assets_dir

    def _parse_maven_library(self, lib: dict) -> tuple[list[str], str | None]:
        """Parse Maven artifact coordinates and return candidate URLs with local destination path."""
        name = lib.get("name")
        if not name:
            return [], None

        parts = name.split(":")
        if len(parts) < 3:
            return [], None

        group = parts[0].replace(".", "/")
        artifact = parts[1]
        version = parts[2]
        classifier = f"-{parts[3]}" if len(parts) > 3 else ""

        rel_path = f"{group}/{artifact}/{version}/{artifact}-{version}{classifier}.jar"
        local_path = os.path.join(self.libraries_dir, os.path.normpath(rel_path))

        # Build candidate download URLs
        urls = []
        custom_url = lib.get("url")
        if custom_url:
            urls.append(f"{custom_url.rstrip('/')}/{rel_path}")

        for repo in self.MAVEN_REPOS:
            repo_url = f"{repo.rstrip('/')}/{rel_path}"
            if repo_url not in urls:
                urls.append(repo_url)

        return urls, local_path

    def _is_lib_allowed(self, lib: dict) -> bool:
        """Check operating system rules for library compatibility."""
        if "rules" not in lib:
            return True
        allowed = False
        for rule in lib["rules"]:
            action = rule.get("action")
            os_rule = rule.get("os", {})
            os_name = os_rule.get("name")

            if action == "allow":
                if not os_rule or os_name == "windows":
                    allowed = True
            elif action == "disallow" and os_name == "windows":
                allowed = False
        return allowed

    def _extract_natives(self, jar_path: str):
        """Extract native binaries (.dll, .so, .dylib) from jar archives."""
        if not os.path.exists(jar_path):
            return
        try:
            with zipfile.ZipFile(jar_path, "r") as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith((".dll", ".so", ".dylib")) and not file.startswith(
                        "META-INF"
                    ):
                        filename = os.path.basename(file)
                        if filename:
                            target_file = os.path.join(self.natives_dir, filename)
                            with (
                                zip_ref.open(file) as source,
                                open(target_file, "wb") as target,
                            ):
                                target.write(source.read())
        except (zipfile.BadZipFile, OSError):
            pass

    def _download_file(self, urls: str | list[str], local_path: str):
        """Helper to download a file from a single URL or candidate URLs with fallback support."""
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        candidate_urls = [urls] if isinstance(urls, str) else urls

        for url in candidate_urls:
            if not url:
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with (
                    urllib.request.urlopen(req, timeout=12) as response,
                    open(local_path, "wb") as f,
                ):
                    f.write(response.read())
                # Successfully downloaded
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    return
            except (urllib.error.URLError, TimeoutError, OSError):
                if os.path.exists(local_path):
                    os.remove(local_path)
                continue

    def download_client_and_libraries(
        self, version_data: dict, version: str, progress_callback=None
    ) -> list:
        """
        Downloads Minecraft client JAR and all required Maven/loader libraries.
        Safely falls back to base vanilla version JSON if 'downloads' key is missing.
        """
        # 1. Resolve client download URL safely
        downloads = version_data.get("downloads", {})
        client_info = downloads.get("client", {})
        client_url = client_info.get("url")

        # Fallback to base Vanilla JSON if custom loader profile (Forge/OptiFine) lacks 'downloads'
        if not client_url:
            base_version = version_data.get("inheritsFrom")
            if not base_version:
                cleaned = version.strip()
                for prefix in ("Forge ", "Fabric ", "OptiFine "):
                    if cleaned.startswith(prefix):
                        cleaned = cleaned.replace(prefix, "").strip()
                        break
                base_version = cleaned

            vanilla_json_path = os.path.join(
                self.versions_dir, base_version, f"{base_version}.json"
            )
            if os.path.exists(vanilla_json_path):
                try:
                    with open(vanilla_json_path, "r", encoding="utf-8") as f:
                        vanilla_data = json.load(f)
                        client_url = (
                            vanilla_data.get("downloads", {})
                            .get("client", {})
                            .get("url")
                        )
                except (OSError, json.JSONDecodeError):
                    pass

        # 2. Download client JAR
        client_jar_path = os.path.join(self.versions_dir, version, f"{version}.jar")
        if client_url and not os.path.exists(client_jar_path):
            if progress_callback:
                progress_callback("Завантаження client.jar...", f"{version}.jar", 0.05)
            self._download_file(client_url, client_jar_path)

        classpath_libs = []
        libs_to_download = version_data.get("libraries", [])
        total_libs = len(libs_to_download)

        # 3. Process and download required libraries
        for index, lib in enumerate(libs_to_download):
            if not self._is_lib_allowed(lib):
                continue

            percent = 0.1 + (index / max(total_libs, 1)) * 0.35
            lib_path = None

            # Standard Mojang artifact download format
            if "downloads" in lib and "artifact" in lib["downloads"]:
                artifact = lib["downloads"]["artifact"]
                lib_path = os.path.join(
                    self.libraries_dir, os.path.normpath(artifact["path"])
                )
                lib_url = artifact.get("url")

                # Fallback URL candidates
                urls, _ = self._parse_maven_library(lib)
                if lib_url and lib_url not in urls:
                    urls.insert(0, lib_url)

                if progress_callback and lib_path:
                    progress_callback(
                        "Завантаження бібліотек", os.path.basename(lib_path), percent
                    )
                self._download_file(urls, lib_path)
                if os.path.exists(lib_path):
                    classpath_libs.append(lib_path)

            # Custom/Forge/Fabric Maven notation library format
            elif "name" in lib:
                urls, lib_path = self._parse_maven_library(lib)
                if urls and lib_path:
                    if progress_callback:
                        progress_callback(
                            "Завантаження бібліотек",
                            os.path.basename(lib_path),
                            percent,
                        )
                    self._download_file(urls, lib_path)
                    if os.path.exists(lib_path):
                        classpath_libs.append(lib_path)

            # Handle native binaries
            if "natives" in lib:
                native_key = lib["natives"].get("windows")
                if native_key:
                    native_key = native_key.replace(
                        "${arch}", "64" if sys.maxsize > 2**32 else "32"
                    )
                    if "downloads" in lib and "classifiers" in lib["downloads"]:
                        classifiers = lib["downloads"]["classifiers"]
                        if native_key in classifiers:
                            native_artifact = classifiers[native_key]
                            native_path = os.path.join(
                                self.libraries_dir,
                                os.path.normpath(native_artifact["path"]),
                            )
                            native_url = native_artifact.get("url")
                            if progress_callback and native_path:
                                progress_callback(
                                    "Завантаження нативів",
                                    os.path.basename(native_path),
                                    percent,
                                )
                            if native_url:
                                self._download_file(native_url, native_path)
                            self._extract_natives(native_path)

            if lib_path and ("natives" in lib_path or "native" in lib_path):
                self._extract_natives(lib_path)

        if os.path.exists(client_jar_path):
            classpath_libs.append(client_jar_path)

        return classpath_libs

    def download_assets(self, version_data: dict, progress_callback=None):
        """Downloads game assets and index manifest using thread pool execution."""
        asset_info = version_data.get("assetIndex", {})
        asset_id = asset_info.get("id")
        asset_url = asset_info.get("url")

        if not asset_id or not asset_url:
            return

        indexes_dir = os.path.join(self.assets_dir, "indexes")
        objects_dir = os.path.join(self.assets_dir, "objects")
        os.makedirs(indexes_dir, exist_ok=True)
        os.makedirs(objects_dir, exist_ok=True)

        index_file_path = os.path.join(indexes_dir, f"{asset_id}.json")
        if not os.path.exists(index_file_path):
            if progress_callback:
                progress_callback("Індекс ресурсів", f"{asset_id}.json", 0.45)
            try:
                req = urllib.request.Request(
                    asset_url, headers={"User-Agent": "Mozilla/5.0"}
                )
                with (
                    urllib.request.urlopen(req, timeout=10) as resp,
                    open(index_file_path, "wb") as f,
                ):
                    f.write(resp.read())
            except (urllib.error.URLError, TimeoutError, OSError):
                return

        try:
            with open(index_file_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        objects = index_data.get("objects", {})
        download_queue = []
        for name, info in objects.items():
            file_hash = info.get("hash")
            if not file_hash:
                continue

            two_chars = file_hash[:2]
            folder_path = os.path.join(objects_dir, two_chars)
            file_path = os.path.join(folder_path, file_hash)

            if not os.path.exists(file_path):
                url = (
                    f"https://resources.download.minecraft.net/{two_chars}/{file_hash}"
                )
                download_queue.append((url, folder_path, file_path, name))

        if not download_queue:
            if progress_callback:
                progress_callback("Ресурси перевірено.", "Усі файли на місці", 0.95)
            return

        downloaded_count = 0
        total_tasks = len(download_queue)

        def download_single_file(task):
            nonlocal downloaded_count
            url, folder_path, file_path, asset_name = task
            try:
                os.makedirs(folder_path, exist_ok=True)
                req = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0"}
                )
                with (
                    urllib.request.urlopen(req, timeout=7) as response,
                    open(file_path, "wb") as f,
                ):
                    f.write(response.read())
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            finally:
                downloaded_count += 1
                if progress_callback:
                    percent = 0.5 + (downloaded_count / total_tasks) * 0.45
                    progress_callback(
                        f"Ресурси: {downloaded_count}/{total_tasks}",
                        os.path.basename(asset_name),
                        percent,
                    )

        with ThreadPoolExecutor(max_workers=16) as executor:
            executor.map(download_single_file, download_queue)