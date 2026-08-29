import os
import json
import urllib.request
import subprocess
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor

class MyLauncherCore:
    def __init__(self, root_dir=None):
        if not root_dir or root_dir.strip() == "":
            local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            self.root_dir = os.path.abspath(os.path.join(local_appdata, "K5Launcher", "game"))
        else:
            self.root_dir = os.path.abspath(root_dir)
            
        self.versions_dir = os.path.join(self.root_dir, "versions")
        self.libraries_dir = os.path.join(self.root_dir, "libraries")
        self.natives_dir = os.path.join(self.root_dir, "natives")
        self.assets_dir = os.path.join(self.root_dir, "assets")
        self.runtime_dir = os.path.join(self.root_dir, "runtime")
        
        os.makedirs(self.versions_dir, exist_ok=True)
        os.makedirs(self.libraries_dir, exist_ok=True)
        os.makedirs(self.natives_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)

    def download_portable_java(self, progress_callback=None):
        if progress_callback:
            progress_callback("Налаштування Java", "Завантаження портативного OpenJDK 21...", 0.01)

        url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3%2B9/OpenJDK21U-jre_x64_windows_hotspot_21.0.3_9.zip"
        zip_path = os.path.join(self.root_dir, "java_temp.zip")
        temp_extract = os.path.join(self.root_dir, "java_extract")

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(resp, out_file)

            if progress_callback:
                progress_callback("Налаштування Java", "Розпаковка Java...", 0.02)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)

            extracted_subfolders = [os.path.join(temp_extract, f) for f in os.listdir(temp_extract) if os.path.isdir(os.path.join(temp_extract, f))]
            if extracted_subfolders:
                if os.path.exists(self.runtime_dir):
                    shutil.rmtree(self.runtime_dir)
                shutil.move(extracted_subfolders[0], self.runtime_dir)

            os.remove(zip_path)
            shutil.rmtree(temp_extract, ignore_errors=True)

            java_exe = os.path.join(self.runtime_dir, "bin", "javaw.exe")
            if not os.path.exists(java_exe):
                java_exe = os.path.join(self.runtime_dir, "bin", "java.exe")
            if os.path.exists(java_exe):
                return java_exe
        except Exception:
            pass

        return "javaw"

    def detect_java_path(self, progress_callback=None):
        local_javaw = os.path.join(self.runtime_dir, "bin", "javaw.exe")
        local_java = os.path.join(self.runtime_dir, "bin", "java.exe")
        if os.path.exists(local_javaw):
            return local_javaw
        elif os.path.exists(local_java):
            return local_java

        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            jh_javaw = os.path.join(java_home, "bin", "javaw.exe")
            jh_exe = os.path.join(java_home, "bin", "java.exe")
            if os.path.exists(jh_javaw):
                return jh_javaw
            elif os.path.exists(jh_exe):
                return jh_exe

        which_javaw = shutil.which("javaw")
        if which_javaw and os.path.exists(which_javaw):
            return which_javaw
        which_java = shutil.which("java")
        if which_java and os.path.exists(which_java):
            return which_java

        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        user_profile = os.environ.get("USERPROFILE", "")

        possible_dirs = [
            os.path.join(program_files, "Java"),
            os.path.join(program_files, "Eclipse Adoptium"),
            os.path.join(program_files, "Microsoft"),
            os.path.join(program_files, "Amazon Corretto"),
            os.path.join(program_files, "Zulu"),
            os.path.join(program_files, "BellSoft"),
            os.path.join(program_files_x86, "Java"),
            os.path.join(user_profile, "AppData", "Local", "Programs", "Eclipse Adoptium"),
            os.path.join(user_profile, "scoop", "apps")
        ]

        found_javas = []
        for base_dir in possible_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                if "javaw.exe" in files:
                    found_javas.append(os.path.join(root, "javaw.exe"))
                elif "java.exe" in files:
                    found_javas.append(os.path.join(root, "java.exe"))

        if found_javas:
            found_javas.sort(reverse=True)
            return found_javas[0]

        return self.download_portable_java(progress_callback)

    def get_release_versions(self):
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        try:
            req = urllib.request.Request(manifest_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                global_manifest = json.loads(response.read().decode())
            releases = [v["id"] for v in global_manifest["versions"] if v["type"] == "release"]
            return releases
        except Exception:
            return ["1.21.1", "1.20.1", "1.19.4", "1.16.5"]

    def get_fabric_loaders(self, game_version):
        loaders_url = f"https://meta.fabricmc.net/v2/versions/loader/{game_version}"
        try:
            req = urllib.request.Request(loaders_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                loaders = json.loads(resp.read().decode())
                return [item["loader"]["version"] for item in loaders if "loader" in item]
        except Exception:
            return []

    def get_version_json(self, version):
        version_json_path = os.path.join(self.versions_dir, version, f"{version}.json")
        if os.path.exists(version_json_path):
            with open(version_json_path, "r", encoding="utf-8") as f:
                return json.load(f)

        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        try:
            req = urllib.request.Request(manifest_url, headers={'User-Agent': 'Mozilla/5.0'})
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
        except Exception as e:
            raise e

    def get_fabric_version_json(self, game_version, loader_version=None):
        if not loader_version:
            loaders = self.get_fabric_loaders(game_version)
            if not loaders:
                raise ValueError(f"Fabric недоступний для версії {game_version}")
            loader_version = loaders[0]

        fabric_url = f"https://meta.fabricmc.net/v2/versions/loader/{game_version}/{loader_version}/profile/json"
        req = urllib.request.Request(fabric_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            fabric_data = json.loads(resp.read().decode())

        vanilla_data = self.get_version_json(game_version)

        merged_data = vanilla_data.copy()
        merged_data["mainClass"] = fabric_data["mainClass"]
        merged_data["libraries"] = fabric_data["libraries"] + vanilla_data["libraries"]
        
        return merged_data

    def _parse_maven_library(self, lib):
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

    def download_client_and_libraries(self, version_data, version, progress_callback=None):
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
                    if rule["action"] == "allow":
                        if "os" in rule and rule["os"]["name"] == "windows":
                            is_allowed = True
                        elif "os" not in rule:
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
                        with urllib.request.urlopen(req, timeout=10) as response:
                            with open(lib_path, "wb") as f:
                                f.write(response.read())
                    except Exception:
                        continue
                
                classpath_libs.append(lib_path)

            if "natives" in lib or "natives-windows" in lib.get("name", ""):
                if lib_path and os.path.exists(lib_path) and lib_path.endswith(".jar"):
                    try:
                        with zipfile.ZipFile(lib_path, 'r') as zip_ref:
                            for file in zip_ref.namelist():
                                if file.endswith(".dll") or file.endswith(".so"):
                                    zip_ref.extract(file, self.natives_dir)
                    except Exception:
                        pass

        classpath_libs.append(client_jar_path)
        return classpath_libs

    def download_assets(self, version_data, progress_callback=None):
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
                with urllib.request.urlopen(req, timeout=7) as response:
                    with open(file_path, "wb") as f:
                        f.write(response.read())
            except Exception:
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

    def launch(self, version, username, java_path=None, ram_gb="4", is_fabric=False, loader_version=None, progress_callback=None):
        if not java_path or java_path.strip() == "" or not os.path.exists(java_path):
            if progress_callback: progress_callback("Конфігурація", "Пошук / Налаштування Java...", 0.01)
            java_path = self.detect_java_path(progress_callback)

        if java_path.endswith("java.exe"):
            javaw_path = java_path[:-8] + "javaw.exe"
            if os.path.exists(javaw_path):
                java_path = javaw_path

        if progress_callback: progress_callback("Маніфест версії", "Отримання конфігурації...", 0.02)
        
        if is_fabric:
            version_data = self.get_fabric_version_json(version, loader_version)
        else:
            version_data = self.get_version_json(version)
        
        classpath_libs = self.download_client_and_libraries(version_data, version, progress_callback)
        self.download_assets(version_data, progress_callback)

        if progress_callback: progress_callback("Збірка конфігурації", "Підготовка аргументів...", 0.98)
        classpath_str = ";".join(classpath_libs)
        main_class = version_data["mainClass"]

        launch_args = [
            java_path,
            f"-Djava.library.path={self.natives_dir}",
            f"-Xmx{ram_gb}G",
            "-cp", classpath_str,
            main_class
        ]

        minecraft_args = [
            "--username", username,
            "--version", f"Fabric-{version}" if is_fabric else version,
            "--gameDir", self.root_dir,
            "--assetsDir", self.assets_dir,
            "--assetIndex", version_data["assetIndex"]["id"],
            "--uuid", "00000000-0000-0000-0000-000000000000",
            "--accessToken", "null",
            "--userType", "legacy"
        ]

        full_command = launch_args + minecraft_args
        if progress_callback: progress_callback("Запуск", "Відкриття Minecraft...", 1.0)
        
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        subprocess.Popen(
            full_command, 
            cwd=self.root_dir,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )