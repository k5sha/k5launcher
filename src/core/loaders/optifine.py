import json
import os
import re
import shutil
import urllib.request
import zipfile

from src.core.loaders.base import BaseLoader
from src.core.loaders.vanilla import VanillaLoader


class OptiFineLoader(BaseLoader):
    OFFICIAL_DOWNLOADS_URL = "https://optifine.net/downloads"
    ADLOAD_BASE_URL = "https://optifine.net/adloadx?f="
    BASE_URL = "https://optifine.net/"

    DEFAULT_SUPPORTED_VERSIONS = (
        "1.21.1",
        "1.20.4",
        "1.20.2",
        "1.20.1",
        "1.19.4",
        "1.19.2",
        "1.18.2",
        "1.16.5",
        "1.12.2",
        "1.8.9",
        "1.7.10",
    )

    def __init__(self, vanilla_loader: VanillaLoader | None = None):
        super().__init__(name="OptiFine")
        self.vanilla_loader = vanilla_loader or VanillaLoader()
        self._cached_version_map = None  # mc_version -> list of filenames

    def fetch_available_versions(self) -> dict[str, list[str]]:
        """
        Scrapes optifine.net/downloads to find all available OptiFine versions.
        Returns a dict: {mc_version: [filename1, filename2, ...]}
        """
        if self._cached_version_map is not None:
            return self._cached_version_map

        version_map: dict[str, list[str]] = {}
        try:
            req = urllib.request.Request(
                self.OFFICIAL_DOWNLOADS_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode("utf-8", errors="ignore")

            matches = re.findall(r"adloadx\?f=([^\"\' >]+)", html)
            for raw_fname in matches:
                fname = raw_fname.split("&")[0].strip()
                match = re.match(
                    r"^(?:preview_)?OptiFine_([0-9\.]+)(?:_([A-Za-z0-9_]+))?\.jar$",
                    fname,
                )
                if match:
                    mc_ver = match.group(1)
                    if mc_ver not in version_map:
                        version_map[mc_ver] = []
                    if fname not in version_map[mc_ver]:
                        version_map[mc_ver].append(fname)
        except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError):
            return {}

        if not version_map:
            for v in self.DEFAULT_SUPPORTED_VERSIONS:
                version_map[v] = [f"OptiFine_{v}_HD_U.jar"]

        self._cached_version_map = version_map
        return self._cached_version_map

    def get_supported_versions(self) -> list[str]:
        return list(self.fetch_available_versions().keys())

    def is_supported(self, mc_version: str) -> bool:
        v_map = self.fetch_available_versions()
        return mc_version in v_map

    def find_best_filename(self, mc_version: str) -> str | None:
        v_map = self.fetch_available_versions()
        files = v_map.get(mc_version, [])
        if not files:
            return None
        stables = [f for f in files if not f.startswith("preview_")]
        if stables:
            return stables[0]
        return files[0]

    def resolve_download_url(self, filename: str) -> str:
        adload_url = f"{self.ADLOAD_BASE_URL}{filename}"
        req = urllib.request.Request(
            adload_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": self.OFFICIAL_DOWNLOADS_URL,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        dl_matches = re.findall(r"href=['\"](downloadx\?f=[^'\"]+)['\"]", html)
        if not dl_matches:
            raise RuntimeError(
                f"Не вдалося отримати посилання для завантаження {filename} з optifine.net"
            )

        return f"{self.BASE_URL}{dl_matches[0]}"

    def download_file_with_progress(
        self, url: str, referer: str, dest_path: str, progress_callback=None
    ):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": referer,
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
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
                            "Завантаження OptiFine",
                            f"{downloaded // 1024} KB / {total_size // 1024} KB",
                            0.1 + pct * 0.35,
                        )

    def install_from_jar(
        self,
        jar_path: str,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        progress_callback=None,
    ) -> str:
        if progress_callback:
            progress_callback("Налаштування OptiFine", "Розпаковка бібліотек...", 0.48)

        with zipfile.ZipFile(jar_path, "r") as z:
            lw_ver = "2.3"
            if "launchwrapper-of.txt" in z.namelist():
                lw_ver = z.read("launchwrapper-of.txt").decode("utf-8").strip()

            filename = os.path.basename(jar_path)
            clean_name = filename.replace("preview_", "").replace(".jar", "")
            parts = clean_name.split("_")
            if len(parts) >= 3:
                of_suffix = "_".join(parts[2:])
            else:
                of_suffix = "HD_U"

            of_version_id = f"{mc_version}-OptiFine_{of_suffix}"

            # 1. Copy OptiFine jar to libraries
            lib_of_dir = os.path.join(
                libraries_dir, "optifine", "OptiFine", f"{mc_version}_{of_suffix}"
            )
            os.makedirs(lib_of_dir, exist_ok=True)
            dest_of_jar = os.path.join(
                lib_of_dir, f"OptiFine-{mc_version}_{of_suffix}.jar"
            )
            shutil.copyfile(jar_path, dest_of_jar)

            # 2. Extract launchwrapper-of if present
            lw_jar_name = f"launchwrapper-of-{lw_ver}.jar"
            if lw_jar_name in z.namelist():
                lib_lw_dir = os.path.join(
                    libraries_dir, "optifine", "launchwrapper-of", lw_ver
                )
                os.makedirs(lib_lw_dir, exist_ok=True)
                dest_lw_jar = os.path.join(lib_lw_dir, lw_jar_name)
                with open(dest_lw_jar, "wb") as f_out:
                    f_out.write(z.read(lw_jar_name))

        # 3. Read base vanilla json
        vanilla_data = self.vanilla_loader.get_version_json(mc_version, versions_dir)

        # 4. Generate OptiFine JSON profile
        of_data = json.loads(json.dumps(vanilla_data))
        of_data["id"] = of_version_id
        of_data["inheritsFrom"] = mc_version
        of_data["mainClass"] = "net.minecraft.launchwrapper.Launch"

        # Tweak arguments
        if "arguments" in of_data:
            game_args = of_data["arguments"].get("game", [])
            if "--tweakClass" not in game_args:
                game_args.extend(["--tweakClass", "optifine.OptiFineTweaker"])
            of_data["arguments"]["game"] = game_args

        if (
            "minecraftArguments" in of_data
            and "--tweakClass" not in of_data["minecraftArguments"]
        ):
            of_data["minecraftArguments"] += " --tweakClass optifine.OptiFineTweaker"

        # Libraries
        of_libs = [
            {"name": f"optifine:OptiFine:{mc_version}_{of_suffix}"},
            {"name": f"optifine:launchwrapper-of:{lw_ver}"},
        ]
        of_data["libraries"] = of_libs + of_data.get("libraries", [])

        # Write of_version_id.json
        of_version_dir = os.path.join(versions_dir, of_version_id)
        os.makedirs(of_version_dir, exist_ok=True)
        of_json_path = os.path.join(of_version_dir, f"{of_version_id}.json")
        with open(of_json_path, "w", encoding="utf-8") as f:
            json.dump(of_data, f, ensure_ascii=False, indent=2)

        return of_version_id

    def ensure_optifine_ready(
        self,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        progress_callback=None,
    ) -> str:
        # Check if already installed
        if os.path.exists(versions_dir):
            for item in os.listdir(versions_dir):
                if item.startswith(f"{mc_version}-OptiFine_"):
                    item_json = os.path.join(versions_dir, item, f"{item}.json")
                    if os.path.exists(item_json):
                        return item

        best_filename = self.find_best_filename(mc_version)
        if not best_filename:
            raise RuntimeError(
                f"Не знайдено сумісної версії OptiFine для Minecraft {mc_version} на optifine.net"
            )

        if progress_callback:
            progress_callback(
                "Пошук OptiFine", f"Отримання посилання {best_filename}...", 0.05
            )

        dl_url = self.resolve_download_url(best_filename)
        referer = f"{self.ADLOAD_BASE_URL}{best_filename}"

        temp_dir = os.path.join(libraries_dir, "optifine", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_jar = os.path.join(temp_dir, best_filename)

        if not os.path.exists(temp_jar) or os.path.getsize(temp_jar) == 0:
            if progress_callback:
                progress_callback(
                    "Завантаження OptiFine",
                    f"Завантаження {best_filename}...",
                    0.1,
                )
            self.download_file_with_progress(
                dl_url, referer, temp_jar, progress_callback
            )

        of_version_id = self.install_from_jar(
            temp_jar, mc_version, versions_dir, libraries_dir, progress_callback
        )
        return of_version_id

    def prepare(
        self,
        mc_version: str,
        versions_dir: str,
        libraries_dir: str,
        loader_version: str | None = None,
        progress_callback=None,
    ) -> tuple[dict, list[str], str]:
        # 1. Ensure base vanilla json exists
        self.vanilla_loader.get_version_json(mc_version, versions_dir)

        # 2. Ensure OptiFine profile and libraries are installed
        of_version_id = self.ensure_optifine_ready(
            mc_version, versions_dir, libraries_dir, progress_callback
        )

        # 3. Read generated OptiFine version JSON
        of_json_path = os.path.join(
            versions_dir, of_version_id, f"{of_version_id}.json"
        )
        with open(of_json_path, "r", encoding="utf-8") as f:
            version_data = json.load(f)

        extra_args = ["--tweakClass", "optifine.OptiFineTweaker"]
        version_label = f"OptiFine-{mc_version}"
        return version_data, extra_args, version_label
