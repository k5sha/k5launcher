import json
import os

from src.utils.helpers import get_app_dir


class ConfigManager:
    def __init__(self, filename="k5launcher_config.json"):
        self.app_dir = get_app_dir()
        self.config_file = os.path.join(self.app_dir, filename)

        self.default_game_dir = os.path.join(self.app_dir, ".minecraft")
        self.game_path = self.default_game_dir
        self.java_path = ""
        self.ram = "4"
        self.username = "Player"
        self.last_version = None
        self.dark_theme = True

        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.game_path = cfg.get("game_path", self.default_game_dir)
                self.java_path = cfg.get("java_path", "")
                self.ram = cfg.get("ram", "4")
                self.username = cfg.get("username", "Player")
                self.last_version = cfg.get("last_version", None)
                self.dark_theme = cfg.get("dark_theme", True)
            except (json.JSONDecodeError, OSError):
                pass

    def save(
        self,
        game_path: str,
        java_path: str,
        ram: str,
        username: str,
        last_version: str,
        dark_theme: bool,
    ):
        self.game_path = game_path.strip()
        self.java_path = java_path.strip()
        self.ram = ram.strip()
        self.username = username.strip()
        self.last_version = last_version
        self.dark_theme = dark_theme

        cfg = {
            "game_path": self.game_path,
            "java_path": self.java_path,
            "ram": self.ram,
            "username": self.username,
            "last_version": self.last_version,
            "dark_theme": self.dark_theme,
        }
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except (OSError, TypeError):
            pass
