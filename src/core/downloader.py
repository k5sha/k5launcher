import json
import os
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

class AssetDownloader:
    def __init__(self, versions_dir: str, libraries_dir: str, natives_dir: str, assets_dir: str):
        self.versions_dir = versions_dir
        self.libraries_dir = libraries_dir
        self.natives_dir = natives_dir
        self.assets_dir = assets_dir

    def _parse_maven_library(self, lib: dict):
        name = lib["name"]
        base_url = lib.get("url", "https://repo1.maven.org/maven2/")
        
        parts = name.split(":")
        group = parts[0].replace(".", "/")
        artifact = parts[1]
        version = parts[2]
        
        rel_path = f"{group}/{artifact}/{version}/{artifact}-{version}.jar"
        full_url = f"{base_url.rstrip('/')}/{rel_path}"
        local_path = os.path.join(self.libraries_dir, os.path.normpath(rel_path))
        
        return full_url, local_path

    def download_client_and_libraries(self, version_data: dict, version: str, progress_callback=None) -> list:
        client_url = version_data["downloads"]["client"]["url"]
        client_jar_path = os.path.join(self.versions_dir, version, f"{version}.jar")
        
        if not os.path.exists(client_jar_path):
            if progress_callback: progress_callback("Завантаження client.jar...", "client.jar", 0.05)
            urllib.request.urlretrieve(client_url, client_jar_path)

        classpath_libs = []
        libs_to_download = version_data["libraries"]
        total_libs = len(libs_to_download)

        for index, lib in enumerate(libs_to_download):
            if "rules" in lib:
                is_allowed = False
                for rule in lib["rules"]:
                    if rule["action"] == "allow" and ("os" not in rule or ("os" in rule and rule["os"]["name"] == "windows")):
                        is_allowed = True
                if not is_allowed:
                    continue

            lib_url = None
            lib_path = None

            if "downloads" in lib and "artifact" in lib["downloads"]:
                artifact = lib["downloads"]["artifact"]
                lib_path = os.path.join(self.libraries_dir, artifact["path"])
                lib_url = artifact["url"]
            elif "name" in lib:
                lib_url, lib_path = self._parse_maven_library(lib)

            if lib_url and lib_path:
                if not os.path.exists(lib_path):
                    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
                    try:
                        percent = 0.1 + (index / total_libs) * 0.35
                        lib_name = os.path.basename(lib_path)
                        if progress_callback: 
                            progress_callback("Завантаження бібліотек", lib_name, percent)
                        
                        req = urllib.request.Request(lib_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=10) as response, open(lib_path, "wb") as f:
                            f.write(response.read())
                    except (urllib.error.URLError, TimeoutError, OSError):
                        continue
                
                classpath_libs.append(lib_path)

            if ("natives" in lib or "natives-windows" in lib.get("name", "")) and lib_path and os.path.exists(lib_path) and lib_path.endswith(".jar"):
                try:
                    with zipfile.ZipFile(lib_path, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if file.endswith((".dll", ".so")):
                                zip_ref.extract(file, self.natives_dir)
                except (zipfile.BadZipFile, OSError):
                    pass

        classpath_libs.append(client_jar_path)
        return classpath_libs

    def download_assets(self, version_data: dict, progress_callback=None):
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
            if progress_callback: progress_callback("Індекс ресурсів", f"{asset_id}.json", 0.45)
            urllib.request.urlretrieve(asset_url, index_file_path)

        with open(index_file_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        objects = index_data.get("objects", {})
        download_queue = []
        for name, info in objects.items():
            file_hash = info.get("hash")
            if not file_hash: continue
            
            two_chars = file_hash[:2]
            folder_path = os.path.join(objects_dir, two_chars)
            file_path = os.path.join(folder_path, file_hash)
            
            if not os.path.exists(file_path):
                url = f"https://resources.download.minecraft.net/{two_chars}/{file_hash}"
                download_queue.append((url, folder_path, file_path, name))

        if not download_queue:
            if progress_callback: progress_callback("Ресурси перевірено.", "Усі файли на місці", 0.95)
            return

        downloaded_count = 0
        total_tasks = len(download_queue)

        def download_single_file(task):
            nonlocal downloaded_count
            url, folder_path, file_path, asset_name = task
            try:
                os.makedirs(folder_path, exist_ok=True)
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=7) as response, open(file_path, "wb") as f:
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
                        percent
                    )

        with ThreadPoolExecutor(max_workers=16) as executor:
            executor.map(download_single_file, download_queue)