import os
import json
import threading
import sys
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from qfluentwidgets import (LineEdit, ComboBox, ProgressBar, PrimaryPushButton, 
                            PushButton, FluentWindow, SwitchButton, CheckBox, setTheme, Theme,
                            ElevatedCardWidget, TitleLabel, BodyLabel, CaptionLabel, 
                            setThemeColor, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class ProgressSignal(QObject):
    progress = pyqtSignal(str, str, float)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error = pyqtSignal(str)
    
    versions_loaded = pyqtSignal(list)
    fabric_loaders_loaded = pyqtSignal(list)


class K5LauncherApp(FluentWindow):
    def __init__(self):
        super().__init__()
        
        setThemeColor('#7b61ff')
        
        app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "K5Launcher")
        os.makedirs(app_dir, exist_ok=True)
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
        self.signals.versions_loaded.connect(self.on_versions_loaded)
        self.signals.fabric_loaders_loaded.connect(self.on_fabric_loaders_loaded)

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

    def load_config(self):
        default_app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "K5Launcher")
        default_game_dir = os.path.join(default_app_dir, "game")
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.game_path = cfg.get("game_path", default_game_dir)
                self.default_java = cfg.get("java_path", "")
                self.default_ram = cfg.get("ram", "4")
                self.saved_username = cfg.get("username", "Player")
                self.saved_version = cfg.get("last_version", None)
                self.is_fabric = cfg.get("is_fabric", False)
                self.saved_fabric_loader = cfg.get("last_fabric_loader", None)
                self.is_dark_theme = cfg.get("dark_theme", True)
                return
            except (json.JSONDecodeError, OSError):
                pass
        
        self.game_path = default_game_dir
        self.default_java = ""
        self.default_ram = "4"
        self.saved_username = "Player"
        self.saved_version = None
        self.is_fabric = False
        self.saved_fabric_loader = None
        self.is_dark_theme = True

    def save_config(self):
        cfg = {
            "game_path": self.entry_dir.text().strip(),
            "java_path": self.entry_java.text().strip(),
            "ram": self.entry_ram.text().strip(),
            "username": self.username_entry.text().strip(),
            "last_version": self.combo_version.currentText(),
            "is_fabric": self.check_fabric.isChecked(),
            "last_fabric_loader": self.combo_fabric_loader.currentText(),
            "dark_theme": self.is_dark_theme
        }
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

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
        self.combo_version.currentTextChanged.connect(self.on_game_version_changed)
        card_layout.addWidget(self.combo_version)

        self.check_fabric = CheckBox("Увімкнути Fabric Loader", card)
        self.check_fabric.setChecked(self.is_fabric)
        self.check_fabric.stateChanged.connect(self.toggle_fabric)
        card_layout.addWidget(self.check_fabric)

        self.combo_fabric_loader = ComboBox(card)
        self.combo_fabric_loader.addItem("Очікування версії...")
        self.combo_fabric_loader.setFixedWidth(350)
        self.combo_fabric_loader.setEnabled(self.is_fabric)
        card_layout.addWidget(self.combo_fabric_loader)

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
        
        self.start_button = PrimaryPushButton(FIF.PLAY_SOLID, "ЗАПУСТИТИ", self.home_interface)
        self.start_button.setFixedSize(220, 46)
        self.start_button.clicked.connect(self.start_launch_thread)
        btn_layout.addWidget(self.start_button)

        self.cancel_button = PushButton(FIF.CLOSE, "ВІДМІНИТИ", self.home_interface)
        self.cancel_button.setFixedSize(220, 46)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.hide()
        
        btn_layout.addWidget(self.cancel_button)
        content_layout.addLayout(btn_layout)
        
        content_layout.addSpacing(6)
        version_label = CaptionLabel("K5Launcher • crafted with 💜 by k5sha", self.home_interface)
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
        self.entry_dir = LineEdit(settings_card)
        self.entry_dir.setText(self.game_path)
        sc_layout.addWidget(self.entry_dir)

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
        self.check_fabric.setEnabled(enabled)
        self.combo_fabric_loader.setEnabled(enabled if self.check_fabric.isChecked() else False)
        self.navigationInterface.setEnabled(enabled)

    def load_versions_async(self):
        try:
            versions = self.launcher_core.get_release_versions()
            self.signals.versions_loaded.emit(versions)
        except Exception as e:
            self.signals.error.emit(f"Помилка завантаження версій: {e}")

    def on_versions_loaded(self, versions):
        self.combo_version.clear()
        self.combo_version.addItems(versions)
        if self.saved_version in versions:
            self.combo_version.setCurrentText(self.saved_version)
            
        if self.check_fabric.isChecked():
            self.load_fabric_loaders_async(self.combo_version.currentText())

    def toggle_fabric(self, state):
        is_checked = self.check_fabric.isChecked()
        self.combo_fabric_loader.setEnabled(is_checked)
        if is_checked:
            self.load_fabric_loaders_async(self.combo_version.currentText())

    def on_game_version_changed(self, version):
        if self.check_fabric.isChecked() and version and version != "Синхронізація...":
            self.load_fabric_loaders_async(version)

    def load_fabric_loaders_async(self, game_version):
        if not game_version or game_version == "Синхронізація...":
            return
        
        def task():
            try:
                loaders = self.launcher_core.get_fabric_loaders(game_version)
                self.signals.fabric_loaders_loaded.emit(loaders)
            except Exception as e:
                self.signals.error.emit(f"Помилка завантаження Fabric: {e}")

        threading.Thread(target=task, daemon=True).start()

    def on_fabric_loaders_loaded(self, loaders):
        self.combo_fabric_loader.clear()
        if loaders:
            self.combo_fabric_loader.addItems(loaders)
            if self.saved_fabric_loader in loaders:
                self.combo_fabric_loader.setCurrentText(self.saved_fabric_loader)
        else:
            self.combo_fabric_loader.addItem("Fabric недоступний")

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
        version = self.combo_version.currentText()
        java_path = self.entry_java.text().strip()
        ram_gb = self.entry_ram.text().strip()
        custom_dir = self.entry_dir.text().strip()
        is_fabric = self.check_fabric.isChecked()
        loader_version = self.combo_fabric_loader.currentText() if is_fabric else None

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

            self.launcher_core.launch(
                version=version, 
                username=username, 
                java_path=java_path, 
                ram_gb=ram_gb, 
                is_fabric=is_fabric,
                loader_version=loader_version,
                progress_callback=self.on_progress
            )
            self.signals.finished.emit()
        except InterruptedError:
            self.signals.canceled.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

    def on_launch_finished(self):
        self.set_ui_state(True)
        self.cancel_button.hide()
        self.start_button.show()
        
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