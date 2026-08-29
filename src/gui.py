import os
import json
import threading
import sys
import time
import urllib.request
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QPixmap, QDesktopServices, QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from qfluentwidgets import (LineEdit, ComboBox, ProgressBar, PrimaryPushButton, 
                            PushButton, TransparentToolButton, FluentWindow, SwitchButton, 
                            setTheme, Theme, ElevatedCardWidget, TitleLabel, BodyLabel, 
                            CaptionLabel, setThemeColor, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF

CURRENT_VERSION = "v1.0.1"

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


class ProgressSignal(QObject):
    progress = pyqtSignal(str, str, float)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error = pyqtSignal(str)
    
    hide_window = pyqtSignal()
    show_window = pyqtSignal()
    
    versions_loaded = pyqtSignal(list)
    update_available = pyqtSignal(str, str)


class K5LauncherApp(FluentWindow):
    def __init__(self):
        super().__init__()
        
        setThemeColor('#7b61ff')
        
        app_icon = resource_path("assets/logo.ico")
        if os.path.exists(app_icon):
            self.setWindowIcon(QIcon(app_icon))
        
        app_dir = get_app_dir()
        self.config_file = os.path.join(app_dir, "k5launcher_config.json")
        
        self.load_config()
        self.cancel_event = threading.Event()
        
        try:
            from src.core import MyLauncherCore
        except ImportError:
            from core import MyLauncherCore

        self.launcher_core = MyLauncherCore(root_dir=self.game_path)
        
        self.signals = ProgressSignal()
        self.signals.progress.connect(self.update_progress_ui)
        self.signals.finished.connect(self.on_launch_finished)
        self.signals.canceled.connect(self.on_launch_canceled)
        self.signals.error.connect(self.on_launch_error)
        self.signals.hide_window.connect(self.hide)
        self.signals.show_window.connect(self.show)
        self.signals.versions_loaded.connect(self.on_versions_loaded)
        self.signals.update_available.connect(self.on_update_available)

        self.setWindowTitle("K5Launcher")
        self.resize(850, 620)
        
        self.home_interface = QWidget(self)
        self.settings_interface = QWidget(self)
        
        self.home_interface.setObjectName("home_interface")
        self.settings_interface.setObjectName("settings_interface")
        
        self.init_home_page()
        self.init_settings_page()
        
        self.addSubInterface(self.home_interface, FIF.HOME, "Головна")
        self.addSubInterface(self.settings_interface, FIF.SETTING, "Налаштування")
        
        setTheme(Theme.DARK if self.is_dark_theme else Theme.LIGHT)
        
        threading.Thread(target=self.load_versions_async, daemon=True).start()
        threading.Thread(target=self.check_updates_async, daemon=True).start()

    def load_config(self):
        app_dir = get_app_dir()
        default_game_dir = os.path.join(app_dir, ".minecraft")
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.game_path = cfg.get("game_path", default_game_dir)
                self.default_java = cfg.get("java_path", "")
                self.default_ram = cfg.get("ram", "4")
                self.saved_username = cfg.get("username", "Player")
                self.saved_version = cfg.get("last_version", None)
                self.is_dark_theme = cfg.get("dark_theme", True)
                return
            except (json.JSONDecodeError, OSError):
                pass
        
        self.game_path = default_game_dir
        self.default_java = ""
        self.default_ram = "4"
        self.saved_username = "Player"
        self.saved_version = None
        self.is_dark_theme = True

    def save_config(self):
        cfg = {
            "game_path": self.entry_dir.text().strip(),
            "java_path": self.entry_java.text().strip(),
            "ram": self.entry_ram.text().strip(),
            "username": self.username_entry.text().strip(),
            "last_version": self.combo_version.currentText(),
            "dark_theme": self.is_dark_theme
        }
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def check_updates_async(self):
        try:
            url = "https://api.github.com/repos/k5sha/k5launcher/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'K5Launcher'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
                latest_version = data.get("tag_name")
                html_url = data.get("html_url", "https://github.com/k5sha/k5launcher/releases")
                if latest_version and latest_version != CURRENT_VERSION:
                    self.signals.update_available.emit(latest_version, html_url)
        except Exception:
            pass

    def on_update_available(self, version, url):
        InfoBar.info(
            title='Доступне оновлення!',
            content=f'Вийшла нова версія {version}. Оновіть додаток на GitHub.',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=10000,
            parent=self
        )

    def open_game_folder(self):
        path = os.path.abspath(self.entry_dir.text().strip() if hasattr(self, 'entry_dir') else self.game_path)
        os.makedirs(path, exist_ok=True)
        if os.name == 'nt':
            os.startfile(path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def init_home_page(self):
        main_layout = QHBoxLayout(self.home_interface)
        main_layout.addStretch(1)
        
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(14)

        logo_path = resource_path("assets/logo.png")
        if os.path.exists(logo_path):
            self.logo_label = QLabel(self.home_interface)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(logo_path).scaled(
                110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(pixmap)
            content_layout.addWidget(self.logo_label)

        self.title_label = TitleLabel("K5LAUNCHER", self.home_interface)
        self.title_label.setStyleSheet("font-size: 32px; font-weight: 800; letter-spacing: 2px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.title_label)

        card = ElevatedCardWidget(self.home_interface)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 25, 35, 25)
        card_layout.setSpacing(14)

        self.username_entry = LineEdit(card)
        self.username_entry.setPlaceholderText("Ігровий нікнейм...")
        self.username_entry.setText(self.saved_username)
        self.username_entry.setFixedWidth(350)
        card_layout.addWidget(self.username_entry)

        self.combo_version = ComboBox(card)
        self.combo_version.addItem("Синхронізація...")
        self.combo_version.setFixedWidth(350)
        card_layout.addWidget(self.combo_version)

        content_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_label = CaptionLabel("Підготовка...", self.home_interface)
        self.log_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_label.hide()
        content_layout.addWidget(self.log_label)

        self.progress_bar = ProgressBar(self.home_interface)
        self.progress_bar.setFixedWidth(380)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        content_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(8)

        self.start_button = PrimaryPushButton(FIF.PLAY_SOLID, "ЗАПУСТИТИ", self.home_interface)
        self.start_button.setFixedSize(200, 46)
        self.start_button.clicked.connect(self.start_launch_thread)
        btn_layout.addWidget(self.start_button)

        self.folder_button = TransparentToolButton(FIF.FOLDER, self.home_interface)
        self.folder_button.setToolTip("Відкрити папку гри")
        self.folder_button.setFixedSize(46, 46)
        self.folder_button.clicked.connect(self.open_game_folder)
        btn_layout.addWidget(self.folder_button)

        self.cancel_button = PushButton(FIF.CLOSE, "ВІДМІНИТИ", self.home_interface)
        self.cancel_button.setFixedSize(200, 46)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.hide()
        btn_layout.addWidget(self.cancel_button)

        content_layout.addLayout(btn_layout)
        
        content_layout.addSpacing(6)
        version_label = CaptionLabel(f"K5Launcher {CURRENT_VERSION} • crafted with 💜 by k5sha", self.home_interface)
        version_label.setStyleSheet("color: #8e8e93; font-weight: 500;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(version_label)

        main_layout.addLayout(content_layout)
        main_layout.addStretch(1)

    def init_settings_page(self):
        main_layout = QHBoxLayout(self.settings_interface)
        main_layout.addStretch(1)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 40, 0, 40)
        content_layout.setSpacing(20)

        title = TitleLabel("Параметри системи", self.settings_interface)
        content_layout.addWidget(title)

        settings_card = ElevatedCardWidget(self.settings_interface)
        settings_card.setFixedWidth(500)
        sc_layout = QVBoxLayout(settings_card)
        sc_layout.setContentsMargins(30, 30, 30, 30)
        sc_layout.setSpacing(20)

        theme_layout = QHBoxLayout()
        theme_layout.addWidget(BodyLabel("Темний режим", settings_card))
        theme_layout.addStretch()
        self.theme_switch = SwitchButton(parent=settings_card)
        self.theme_switch.setChecked(self.is_dark_theme)
        self.theme_switch.checkedChanged.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_switch)
        sc_layout.addLayout(theme_layout)

        sc_layout.addWidget(BodyLabel("Шлях до Java (залиште порожнім для автопошуку):", settings_card))
        self.entry_java = LineEdit(settings_card)
        self.entry_java.setText(self.default_java)
        self.entry_java.setPlaceholderText("Автоматично")
        sc_layout.addWidget(self.entry_java)

        sc_layout.addWidget(BodyLabel("Виділення пам'яті (ГБ):", settings_card))
        self.entry_ram = LineEdit(settings_card)
        self.entry_ram.setText(self.default_ram)
        self.entry_ram.setFixedWidth(150)
        sc_layout.addWidget(self.entry_ram)

        sc_layout.addWidget(BodyLabel("Папка гри:", settings_card))
        dir_layout = QHBoxLayout()
        self.entry_dir = LineEdit(settings_card)
        self.entry_dir.setText(self.game_path)
        
        self.btn_open_dir_settings = TransparentToolButton(FIF.FOLDER, settings_card)
        self.btn_open_dir_settings.setToolTip("Відкрити у Провіднику")
        self.btn_open_dir_settings.clicked.connect(self.open_game_folder)
        
        dir_layout.addWidget(self.entry_dir)
        dir_layout.addWidget(self.btn_open_dir_settings)
        sc_layout.addLayout(dir_layout)

        content_layout.addWidget(settings_card)
        content_layout.addStretch()
        
        main_layout.addLayout(content_layout)
        main_layout.addStretch(1)

    def toggle_theme(self, is_dark):
        self.is_dark_theme = is_dark
        setTheme(Theme.DARK if is_dark else Theme.LIGHT)
        self.save_config()

    def set_ui_state(self, enabled):
        self.username_entry.setEnabled(enabled)
        self.combo_version.setEnabled(enabled)
        self.folder_button.setEnabled(enabled)
        self.navigationInterface.setEnabled(enabled)

    def load_versions_async(self):
        try:
            versions = self.launcher_core.get_release_versions()
            self.signals.versions_loaded.emit(versions)
        except Exception as e:
            self.signals.error.emit(f"Помилка завантаження версій: {e}")

    def on_versions_loaded(self, versions):
        self.combo_version.clear()
        combined_list = []
        for v in versions:
            combined_list.append(v)
            combined_list.append(f"Fabric {v}")

        self.combo_version.addItems(combined_list)
        if self.saved_version in combined_list:
            self.combo_version.setCurrentText(self.saved_version)

    def cancel_download(self):
        self.cancel_event.set()
        self.log_label.setText("Переривання завантаження...")
        self.cancel_button.setEnabled(False)

    def on_progress(self, status_text, current_file, progress_value):
        if self.cancel_event.is_set():
            raise InterruptedError()
        self.signals.progress.emit(status_text, current_file, progress_value)

    def update_progress_ui(self, status, file, value):
        self.log_label.setText(f"{status}: {file}")
        self.progress_bar.setValue(int(value * 100))

    def start_launch_thread(self):
        self.save_config()
        self.cancel_event.clear()
        
        self.start_button.hide()
        self.folder_button.hide()
        self.cancel_button.show()
        self.cancel_button.setEnabled(True)
        
        self.progress_bar.show()
        self.log_label.show()
        self.progress_bar.setValue(0)
        self.log_label.setText("Ініціалізація...")
        
        self.set_ui_state(False)
        
        threading.Thread(target=self.launch_game, daemon=True).start()

    def launch_game(self):
        username = self.username_entry.text().strip()
        version_str = self.combo_version.currentText()
        java_path = self.entry_java.text().strip()
        ram_gb = self.entry_ram.text().strip()
        custom_dir = self.entry_dir.text().strip()

        if not username:
            self.signals.error.emit("Ім'я користувача не може бути порожнім.")
            return

        try:
            self.launcher_core.root_dir = os.path.abspath(custom_dir)
            self.launcher_core.versions_dir = os.path.join(self.launcher_core.root_dir, "versions")
            self.launcher_core.libraries_dir = os.path.join(self.launcher_core.root_dir, "libraries")
            self.launcher_core.natives_dir = os.path.join(self.launcher_core.root_dir, "natives")
            self.launcher_core.assets_dir = os.path.join(self.launcher_core.root_dir, "assets")
            self.launcher_core.runtime_dir = os.path.join(self.launcher_core.root_dir, "runtime")

            process = self.launcher_core.launch(
                version=version_str, 
                username=username, 
                java_path=java_path, 
                ram_gb=ram_gb,
                progress_callback=self.on_progress
            )

            if process:
                time.sleep(3)
                self.signals.hide_window.emit()
                exit_code = process.wait()
                self.signals.show_window.emit()

                if exit_code != 0:
                    self.signals.error.emit(f"Гра завершилася з помилкою (код виходу: {exit_code}).")
                    return

            self.signals.finished.emit()
        except InterruptedError:
            self.signals.show_window.emit()
            self.signals.canceled.emit()
        except Exception as e:
            self.signals.show_window.emit()
            self.signals.error.emit(str(e))

    def on_launch_finished(self):
        self.set_ui_state(True)
        self.cancel_button.hide()
        self.start_button.show()
        self.folder_button.show()
        
        self.progress_bar.hide()
        self.log_label.hide()

    def on_launch_canceled(self):
        self.on_launch_finished()
        InfoBar.warning(
            title='Відмінено',
            content="Завантаження перервано користувачем",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self
        )

    def on_launch_error(self, err_msg):
        self.on_launch_finished()
        InfoBar.error(
            title='Помилка запуску',
            content=err_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = K5LauncherApp()
    w.show()
    sys.exit(app.exec())