import os
import subprocess
import sys

from src.core.downloader import AssetDownloader
from src.core.java import JavaManager
from src.core.versions import VersionManager


class MyLauncherCore:
    def __init__(self, root_dir=None):
        if not root_dir or root_dir.strip() == "":
            base_dir = (
                os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.abspath(".")
            )
            self.root_dir = os.path.abspath(os.path.join(base_dir, ".minecraft"))
        else:
            self.root_dir = os.path.abspath(root_dir)

        self._update_paths()

    def _update_paths(self):
        self.versions_dir = os.path.join(self.root_dir, "versions")
        self.libraries_dir = os.path.join(self.root_dir, "libraries")
        self.natives_dir = os.path.join(self.root_dir, "natives")
        self.assets_dir = os.path.join(self.root_dir, "assets")
        self.runtimes_base_dir = os.path.join(self.root_dir, "runtimes")

        for d in [
            self.versions_dir,
            self.libraries_dir,
            self.natives_dir,
            self.assets_dir,
            self.runtimes_base_dir,
        ]:
            os.makedirs(d, exist_ok=True)

        self.java_manager = JavaManager(self.runtimes_base_dir, self.root_dir)
        self.version_manager = VersionManager(self.versions_dir)
        self.downloader = AssetDownloader(
            self.versions_dir, self.libraries_dir, self.natives_dir, self.assets_dir
        )

    def update_root_dir(self, new_root_dir: str):
        self.root_dir = os.path.abspath(new_root_dir)
        self._update_paths()

    def get_release_versions(self):
        return self.version_manager.get_release_versions()

    def launch(
        self,
        version,
        username,
        java_path=None,
        ram_gb="4",
        is_fabric=False,
        loader_version=None,
        progress_callback=None,
    ):
        if version.startswith("Fabric "):
            is_fabric = True
            version = version.replace("Fabric ", "").strip()

        if progress_callback:
            progress_callback("Маніфест версії", "Отримання конфігурації...", 0.02)

        if is_fabric:
            version_data = self.version_manager.get_fabric_version_json(
                version, loader_version
            )
        else:
            version_data = self.version_manager.get_version_json(version)

        java_version_info = version_data.get("javaVersion", {})
        target_java_major = java_version_info.get("majorVersion", 8)
        target_java_major = min(target_java_major, 25)

        if (
            java_path
            and java_path.strip() != ""
            and os.path.exists(java_path)
            and not self.java_manager.check_java_version(java_path, target_java_major)
        ):
            java_path = None

        if not java_path or java_path.strip() == "" or not os.path.exists(java_path):
            if progress_callback:
                progress_callback(
                    "Конфігурація",
                    f"Пошук / Налаштування Java {target_java_major}...",
                    0.01,
                )
            java_path = self.java_manager.detect_java_path(
                target_java_major, progress_callback
            )

        if java_path.endswith("java.exe"):
            javaw_path = java_path[:-8] + "javaw.exe"
            if os.path.exists(javaw_path):
                java_path = javaw_path

        classpath_libs = self.downloader.download_client_and_libraries(
            version_data, version, progress_callback
        )
        self.downloader.download_assets(version_data, progress_callback)

        if progress_callback:
            progress_callback("Збірка конфігурації", "Підготовка аргументів...", 0.98)
        classpath_str = ";".join(classpath_libs)
        main_class = version_data["mainClass"]

        launch_args = [
            java_path,
            f"-Djava.library.path={self.natives_dir}",
            f"-Xmx{ram_gb}G",
            "-cp",
            classpath_str,
            main_class,
        ]

        minecraft_args = [
            "--username",
            username,
            "--version",
            f"Fabric-{version}" if is_fabric else version,
            "--gameDir",
            self.root_dir,
            "--assetsDir",
            self.assets_dir,
            "--assetIndex",
            version_data["assetIndex"]["id"],
            "--uuid",
            "00000000-0000-0000-0000-000000000000",
            "--accessToken",
            "null",
            "--userProperties",
            "{}",
            "--userType",
            "legacy",
        ]

        full_command = launch_args + minecraft_args
        if progress_callback:
            progress_callback("Запуск", "Відкриття Minecraft...", 1.0)

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        log_path = os.path.join(self.root_dir, "launcher_error.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                full_command,
                cwd=self.root_dir,
                creationflags=creationflags,
                stdout=log_file,
                stderr=log_file,
            )

        return process
