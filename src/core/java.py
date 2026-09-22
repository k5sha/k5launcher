import os
import shutil
import subprocess
import urllib.request
import zipfile

class JavaManager:
    def __init__(self, runtimes_base_dir: str, root_dir: str):
        self.runtimes_base_dir = runtimes_base_dir
        self.root_dir = root_dir

    def _get_java_download_info(self, major_version: int):
        java_sources = {
            8: ("https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u412-b08/OpenJDK8U-jre_x64_windows_hotspot_8u412b08.zip", "jdk8u412-b08"),
            11: ("https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.23%2B9/OpenJDK11U-jre_x64_windows_hotspot_11.0.23_9.zip", "jdk-11.0.23+9"),
            17: ("https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jre_x64_windows_hotspot_17.0.11_9.zip", "jdk-17.0.11+9"),
            21: ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.3%2B9/OpenJDK21U-jre_x64_windows_hotspot_21.0.3_9.zip", "jdk-21.0.3+9"),
            25: ("https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25%2B36/OpenJDK25U-jre_x64_windows_hotspot_25_36.zip", "jdk-25+36")
        }
        return java_sources.get(major_version, java_sources[25])

    def check_java_version(self, java_path: str, required_major: int) -> bool:
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=3,
                check=False
            )
            version_output = result.stderr + result.stdout
            
            if f'version "{required_major}.' in version_output or f'version "{required_major}' in version_output:
                return True
            if required_major == 8 and ("1.8." in version_output):
                return True
            if f'"{required_major}.' in version_output or f'"{required_major}+' in version_output:
                return True
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        return False

    def download_portable_java(self, major_version=21, progress_callback=None) -> str:
        target_runtime_dir = os.path.join(self.runtimes_base_dir, f"java_{major_version}")
        
        java_exe = os.path.join(target_runtime_dir, "bin", "javaw.exe")
        if not os.path.exists(java_exe):
            java_exe = os.path.join(target_runtime_dir, "bin", "java.exe")
            
        if os.path.exists(java_exe) and self.check_java_version(java_exe, major_version):
            return java_exe

        if progress_callback:
            progress_callback("Налаштування Java", f"Завантаження портативного OpenJDK {major_version}...", 0.01)

        url, _ = self._get_java_download_info(major_version)
        zip_path = os.path.join(self.root_dir, f"java_temp_{major_version}.zip")
        temp_extract = os.path.join(self.root_dir, f"java_extract_{major_version}")

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out_file:
                shutil.copyfileobj(resp, out_file)

            if progress_callback:
                progress_callback("Налаштування Java", f"Розпаковка Java {major_version}...", 0.02)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)

            extracted_subfolders = [os.path.join(temp_extract, f) for f in os.listdir(temp_extract) if os.path.isdir(os.path.join(temp_extract, f))]
            if extracted_subfolders:
                if os.path.exists(target_runtime_dir):
                    shutil.rmtree(target_runtime_dir)
                shutil.move(extracted_subfolders[0], target_runtime_dir)

            os.remove(zip_path)
            shutil.rmtree(temp_extract, ignore_errors=True)

            java_exe = os.path.join(target_runtime_dir, "bin", "javaw.exe")
            if not os.path.exists(java_exe):
                java_exe = os.path.join(target_runtime_dir, "bin", "java.exe")
                
            if os.path.exists(java_exe):
                return java_exe
        except (urllib.error.URLError, zipfile.BadZipFile, OSError):
            pass

        return "javaw"

    def detect_java_path(self, required_major=21, progress_callback=None) -> str:
        target_runtime_dir = os.path.join(self.runtimes_base_dir, f"java_{required_major}")
        for exe_name in ["javaw.exe", "java.exe"]:
            local_path = os.path.join(target_runtime_dir, "bin", exe_name)
            if os.path.exists(local_path) and self.check_java_version(local_path, required_major):
                return local_path

        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            for exe_name in ["javaw.exe", "java.exe"]:
                jh_path = os.path.join(java_home, "bin", exe_name)
                if os.path.exists(jh_path) and self.check_java_version(jh_path, required_major):
                    return jh_path

        for cmd in ["javaw", "java"]:
            which_path = shutil.which(cmd)
            if which_path and os.path.exists(which_path) and self.check_java_version(which_path, required_major):
                return which_path

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
        ]

        for base_dir in possible_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                for exe_name in ["javaw.exe", "java.exe"]:
                    if exe_name in files:
                        candidate = os.path.join(root, exe_name)
                        if self.check_java_version(candidate, required_major):
                            return candidate

        return self.download_portable_java(required_major, progress_callback)