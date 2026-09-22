import os
import subprocess
import threading
import time
import urllib.error
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon
from qfluentwidgets import FluentWindow, InfoBar, InfoBarPosition, Theme, setTheme, setThemeColor
from qfluentwidgets import FluentIcon as FIF

from src.config.settings import ConfigManager
from src.core.launcher import MyLauncherCore
from src.ui.signals import ProgressSignal
from src.ui.views.home_view import HomeInterface
from src.ui.views.settings_view import SettingsInterface
from src.utils.helpers import resource_path
from src.utils.updater import check_for_updates

class K5LauncherApp(FluentWindow):
    def __init__(self):
        super().__init__()
        
        setThemeColor('#7b61ff')
        
        app_icon = resource_path("assets/logo.ico")
        if os.path.exists(app_icon):
            self.setWindowIcon(QIcon(app_icon))
        
        self.config = ConfigManager()
        self.cancel_event = threading.Event()
        self.launcher_core = MyLauncherCore(root_dir=self.config.game_path)
        
        self.signals = ProgressSignal()
        self.setup_signals()

        self.setWindowTitle("K5Launcher")
        self.resize(850, 620)
        
        self.home_interface = HomeInterface(self)
        self.settings_interface = SettingsInterface(self)
        
        self.addSubInterface(self.home_interface, FIF.HOME, "Головна")
        self.addSubInterface(self.settings_interface, FIF.SETTING, "Налаштування")
        
        self.load_values_to_ui()
        self.bind_events()
        
        setTheme(Theme.DARK if self.config.dark_theme else Theme.LIGHT)
        
        threading.Thread(target=self.load_versions_async, daemon=True).start()
        threading.Thread(target=self.check_updates_async, daemon=True).start()

    def setup_signals(self):
        self.signals.progress.connect(self.update_progress_ui)
        self.signals.finished.connect(self.on_launch_finished)
        self.signals.canceled.connect(self.on_launch_canceled)
        self.signals.error.connect(self.on_launch_error)
        self.signals.hide_window.connect(self.hide)
        self.signals.show_window.connect(self.show)
        self.signals.versions_loaded.connect(self.on_versions_loaded)
        self.signals.update_available.connect(self.on_update_available)

    def load_values_to_ui(self):
        # Home page
        self.home_interface.username_entry.setText(self.config.username)
        
        # Settings page
        self.settings_interface.theme_switch.setChecked(self.config.dark_theme)
        self.settings_interface.entry_java.setText(self.config.java_path)
        self.settings_interface.entry_ram.setText(self.config.ram)
        self.settings_interface.entry_dir.setText(self.config.game_path)

    def bind_events(self):
        self.home_interface.start_button.clicked.connect(self.start_launch_thread)
        self.home_interface.folder_button.clicked.connect(self.open_game_folder)
        self.home_interface.cancel_button.clicked.connect(self.cancel_download)

        self.settings_interface.btn_open_dir_settings.clicked.connect(self.open_game_folder)
        self.settings_interface.theme_switch.checkedChanged.connect(self.toggle_theme)

    def save_current_config(self):
        self.config.save(
            game_path=self.settings_interface.entry_dir.text(),
            java_path=self.settings_interface.entry_java.text(),
            ram=self.settings_interface.entry_ram.text(),
            username=self.home_interface.username_entry.text(),
            last_version=self.home_interface.combo_version.currentText(),
            dark_theme=self.config.dark_theme
        )

    def check_updates_async(self):
        ver, url = check_for_updates()
        if ver:
            self.signals.update_available.emit(ver, url)

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
        path = os.path.abspath(self.settings_interface.entry_dir.text().strip())
        os.makedirs(path, exist_ok=True)
        if os.name == 'nt':
            os.startfile(path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def toggle_theme(self, is_dark):
        self.config.dark_theme = is_dark
        setTheme(Theme.DARK if is_dark else Theme.LIGHT)
        self.save_current_config()

    def set_ui_state(self, enabled):
        self.home_interface.username_entry.setEnabled(enabled)
        self.home_interface.combo_version.setEnabled(enabled)
        self.home_interface.folder_button.setEnabled(enabled)
        self.navigationInterface.setEnabled(enabled)

    def load_versions_async(self):
        try:
            versions = self.launcher_core.get_release_versions()
            self.signals.versions_loaded.emit(versions)
        except (urllib.error.URLError, Exception) as e:
            self.signals.error.emit(f"Помилка завантаження версій: {e}")

    def on_versions_loaded(self, versions):
        self.home_interface.combo_version.clear()
        combined_list = []
        for v in versions:
            combined_list.append(v)
            combined_list.append(f"Fabric {v}")

        self.home_interface.combo_version.addItems(combined_list)
        if self.config.last_version in combined_list:
            self.home_interface.combo_version.setCurrentText(self.config.last_version)

    def cancel_download(self):
        self.cancel_event.set()
        self.home_interface.log_label.setText("Переривання завантаження...")
        self.home_interface.cancel_button.setEnabled(False)

    def on_progress(self, status_text, current_file, progress_value):
        if self.cancel_event.is_set():
            raise InterruptedError()
        self.signals.progress.emit(status_text, current_file, progress_value)

    def update_progress_ui(self, status, file, value):
        self.home_interface.log_label.setText(f"{status}: {file}")
        self.home_interface.progress_bar.setValue(int(value * 100))

    def start_launch_thread(self):
        self.save_current_config()
        self.cancel_event.clear()
        
        self.home_interface.start_button.hide()
        self.home_interface.folder_button.hide()
        self.home_interface.cancel_button.show()
        self.home_interface.cancel_button.setEnabled(True)
        
        self.home_interface.progress_bar.show()
        self.home_interface.log_label.show()
        self.home_interface.progress_bar.setValue(0)
        self.home_interface.log_label.setText("Ініціалізація...")
        
        self.set_ui_state(False)
        
        threading.Thread(target=self.launch_game, daemon=True).start()

    def launch_game(self):
        username = self.home_interface.username_entry.text().strip()
        version_str = self.home_interface.combo_version.currentText()
        java_path = self.settings_interface.entry_java.text().strip()
        ram_gb = self.settings_interface.entry_ram.text().strip()
        custom_dir = self.settings_interface.entry_dir.text().strip()

        if not username:
            self.signals.error.emit("Ім'я користувача не може бути порожнім.")
            return

        try:
            self.launcher_core.update_root_dir(custom_dir)

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
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            self.signals.show_window.emit()
            self.signals.error.emit(str(e))

    def on_launch_finished(self):
        self.set_ui_state(True)
        self.home_interface.cancel_button.hide()
        self.home_interface.start_button.show()
        self.home_interface.folder_button.show()
        
        self.home_interface.progress_bar.hide()
        self.home_interface.log_label.hide()

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