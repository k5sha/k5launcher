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

    def get_selectable_versions(self):
        return self.version_manager.get_all_selectable_versions()

    def get_optifine_supported_versions(self):
        return self.version_manager.get_optifine_supported_versions()

    def get_fabric_supported_versions(self):
        return self.version_manager.get_fabric_supported_versions()

    def get_forge_supported_versions(self):
        return self.version_manager.get_forge_supported_versions()

    def _parse_jvm_arguments(
        self, version_data: dict, version_label: str, classpath_str: str
    ) -> list[str]:
        """Parses JVM arguments from version manifest, resolving placeholders and @args files."""
        jvm_args = []
        raw_jvm = version_data.get("arguments", {}).get("jvm", [])

        cp_sep = ";" if os.name == "nt" else ":"
        replacements = {
            "${natives_directory}": self.natives_dir,
            "${launcher_name}": "K5Launcher",
            "${launcher_version}": "1.0.0",
            "${classpath}": classpath_str,
            "${classpath_separator}": cp_sep,
            "${library_directory}": self.libraries_dir,
            "${version_name}": version_label,
        }

        for item in raw_jvm:
            val_list = []
            if isinstance(item, str):
                val_list = [item]
            elif isinstance(item, dict):
                rules = item.get("rules", [])
                allowed = True
                for rule in rules:
                    action = rule.get("action")
                    os_rule = rule.get("os", {})
                    os_name = os_rule.get("name")
                    current_os = "windows" if os.name == "nt" else "linux"

                    if action == "allow":
                        if os_rule and os_name != current_os:
                            allowed = False
                    elif action == "disallow":
                        if os_rule and os_name == current_os:
                            allowed = False

                if allowed:
                    raw_val = item.get("value", [])
                    val_list = [raw_val] if isinstance(raw_val, str) else raw_val

            for val in val_list:
                for k, v in replacements.items():
                    val = val.replace(k, v)

                # Convert relative @argument_file paths to absolute paths
                if val.startswith("@") and not os.path.isabs(val[1:]):
                    arg_rel_path = val[1:]
                    candidate_path = os.path.join(self.root_dir, arg_rel_path)
                    if not os.path.exists(candidate_path):
                        if arg_rel_path.startswith("libraries/"):
                            candidate_path = os.path.join(
                                self.libraries_dir, arg_rel_path.replace("libraries/", "", 1)
                            )
                    val = f"@{candidate_path}"

                jvm_args.append(val)

        return jvm_args

    def _parse_game_arguments(
        self, version_data: dict, version_label: str, username: str, asset_id: str
    ) -> list[str]:
        """Parses game arguments from version manifest, resolving placeholders and filtering optional features."""
        raw_game = version_data.get("arguments", {}).get("game", [])
        game_args = []

        replacements = {
            "${auth_player_name}": username,
            "${version_name}": version_label,
            "${game_directory}": self.root_dir,
            "${assets_root}": self.assets_dir,
            "${assets_index_name}": asset_id,
            "${auth_uuid}": "00000000-0000-0000-0000-000000000000",
            "${auth_access_token}": "null",
            "${user_type}": "legacy",
            "${version_type}": version_data.get("type", "release"),
            "${user_properties}": "{}",
            "${resolution_width}": "854",
            "${resolution_height}": "480",
            "${clientid}": "",
            "${clientId}": "",
            "${auth_xuid}": "",
        }

        if raw_game:
            for item in raw_game:
                val_list = []
                if isinstance(item, str):
                    val_list = [item]
                elif isinstance(item, dict):
                    rules = item.get("rules", [])
                    allowed = True
                    for rule in rules:
                        action = rule.get("action")
                        features = rule.get("features", {})
                        os_rule = rule.get("os", {})

                        # Ignore optional feature flags (like quickPlay, demo mode) unless explicitly supported
                        if features:
                            allowed = False

                        if os_rule:
                            os_name = os_rule.get("name")
                            current_os = "windows" if os.name == "nt" else "linux"
                            if action == "allow" and os_name != current_os:
                                allowed = False
                            elif action == "disallow" and os_name == current_os:
                                allowed = False

                    if allowed:
                        raw_val = item.get("value", [])
                        val_list = [raw_val] if isinstance(raw_val, str) else raw_val

                for val in val_list:
                    for k, v in replacements.items():
                        val = val.replace(k, v)
                    game_args.append(val)

        # Fallback to legacy minecraftArguments string if arguments.game is empty
        if not game_args:
            legacy_args = version_data.get("minecraftArguments", "")
            if legacy_args:
                for token in legacy_args.split():
                    for k, v in replacements.items():
                        token = token.replace(k, v)
                    game_args.append(token)

        # Post-process: strip flag-value pairs with empty values or unresolved placeholders
        cleaned_args = []
        skip_next = False
        for i in range(len(game_args)):
            if skip_next:
                skip_next = False
                continue

            current = game_args[i]
            next_val = game_args[i + 1] if i + 1 < len(game_args) else None

            if current.startswith("--") and next_val and (next_val.startswith("${") or next_val == ""):
                skip_next = True
                continue

            if current.startswith("${"):
                continue

            cleaned_args.append(current)

        game_args = cleaned_args

        # Mandatory options required by Minecraft client
        required_defaults = [
            ("--username", username),
            ("--version", version_label),
            ("--gameDir", self.root_dir),
            ("--assetsDir", self.assets_dir),
            ("--assetIndex", asset_id),
            ("--uuid", "00000000-0000-0000-0000-000000000000"),
            ("--accessToken", "null"),
            ("--userType", "legacy"),
        ]

        for flag, default_val in required_defaults:
            if flag not in game_args:
                game_args.extend([flag, default_val])

        # Ensure --launchTarget is provided for Forge / ModLauncher
        if "--launchTarget" not in game_args and ("Forge" in version_label or "forge" in version_data.get("id", "")):
            game_args.extend(["--launchTarget", "forgeclient"])

        return game_args

    def launch(
        self,
        version,
        username,
        java_path=None,
        ram_gb="4",
        loader_version=None,
        progress_callback=None,
        **kwargs,
    ):
        if progress_callback:
            progress_callback("Конфігурація", "Підготовка профілю версії...", 0.02)

        _, mc_version = self.version_manager.parse_version_string(version)

        # 1. Determine target Java major version dynamically
        target_java_major = self.version_manager.get_required_java_major(mc_version)

        # Validate custom java path if provided
        if (
            java_path
            and java_path.strip() != ""
            and os.path.exists(java_path)
            and not self.java_manager.check_java_version(java_path, target_java_major)
        ):
            java_path = None

        # Detect or download suitable OpenJDK runtime
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

        # 2. Prepare profile (Forge, Fabric, OptiFine or Vanilla)
        version_data, extra_args, version_label = self.version_manager.prepare_version(
            version_str=version,
            libraries_dir=self.libraries_dir,
            loader_version=loader_version,
            progress_callback=progress_callback,
        )

        # Re-check java major version if explicit javaVersion manifest exists in version_data
        explicit_java_major = self.version_manager.get_required_java_major(
            mc_version, version_data
        )
        if explicit_java_major > target_java_major:
            target_java_major = explicit_java_major
            java_path = self.java_manager.detect_java_path(
                target_java_major, progress_callback
            )
            if java_path.endswith("java.exe"):
                javaw_path = java_path[:-8] + "javaw.exe"
                if os.path.exists(javaw_path):
                    java_path = javaw_path

        # 3. Download client JAR, libraries, and game assets
        classpath_libs = self.downloader.download_client_and_libraries(
            version_data, mc_version, progress_callback
        )
        self.downloader.download_assets(version_data, progress_callback)

        if progress_callback:
            progress_callback("Збірка конфігурації", "Підготовка аргументів...", 0.98)

        classpath_str = ";".join(classpath_libs)
        main_class = version_data.get("mainClass", "net.minecraft.client.main.Main")

        # Unlock experimental VM flags and ignore unrecognized options
        default_jvm_flags = [
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+IgnoreUnrecognizedVMOptions",
            f"-Xmx{ram_gb}G",
            "-Xms512M",
            f"-Djava.library.path={self.natives_dir}",
            "-XX:+UseG1GC",
            "-Dfile.encoding=UTF-8",
        ]

        if target_java_major >= 17:
            default_jvm_flags.append("--enable-native-access=ALL-UNNAMED")

        # Parse specific JVM flags from version JSON (crucial for Forge ModLauncher / win_args.txt)
        parsed_jvm_flags = self._parse_jvm_arguments(
            version_data, version_label, classpath_str
        )

        if parsed_jvm_flags:
            jvm_flags = default_jvm_flags + parsed_jvm_flags
            if "-cp" not in jvm_flags and "-classpath" not in jvm_flags:
                jvm_flags.extend(["-cp", classpath_str])
        else:
            jvm_flags = default_jvm_flags + ["-cp", classpath_str]

        launch_args = [java_path] + jvm_flags + [main_class]

        # Safely extract asset index ID with fallback options
        asset_info = version_data.get("assetIndex")
        if isinstance(asset_info, dict) and "id" in asset_info:
            asset_id = asset_info["id"]
        else:
            asset_id = version_data.get("assets", mc_version)

        # Build game launch arguments dynamically from profile manifest
        minecraft_args = self._parse_game_arguments(
            version_data, version_label, username, asset_id
        ) + extra_args

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