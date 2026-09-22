import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    ComboBox,
    ElevatedCardWidget,
    LineEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    TitleLabel,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from src.utils.helpers import resource_path
from src.utils.updater import CURRENT_VERSION


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("home_interface")
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.addStretch(1)

        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(14)

        logo_path = resource_path("assets/logo.png")
        if os.path.exists(logo_path):
            self.logo_label = QLabel(self)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(logo_path).scaled(
                110,
                110,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(pixmap)
            content_layout.addWidget(self.logo_label)

        self.title_label = TitleLabel("K5LAUNCHER", self)
        self.title_label.setStyleSheet(
            "font-size: 32px; font-weight: 800; letter-spacing: 2px;"
        )
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.title_label)

        card = ElevatedCardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(35, 25, 35, 25)
        card_layout.setSpacing(14)

        self.username_entry = LineEdit(card)
        self.username_entry.setPlaceholderText("Ігровий нікнейм...")
        self.username_entry.setFixedWidth(350)
        card_layout.addWidget(self.username_entry)

        self.combo_version = ComboBox(card)
        self.combo_version.addItem("Синхронізація...")
        self.combo_version.setFixedWidth(350)
        card_layout.addWidget(self.combo_version)

        content_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_label = CaptionLabel("Підготовка...", self)
        self.log_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_label.hide()
        content_layout.addWidget(self.log_label)

        self.progress_bar = ProgressBar(self)
        self.progress_bar.setFixedWidth(380)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        content_layout.addWidget(
            self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter
        )

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(8)

        self.start_button = PrimaryPushButton(FIF.PLAY_SOLID, "ЗАПУСТИТИ", self)
        self.start_button.setFixedSize(200, 46)
        btn_layout.addWidget(self.start_button)

        self.folder_button = TransparentToolButton(FIF.FOLDER, self)
        self.folder_button.setToolTip("Відкрити папку гри")
        self.folder_button.setFixedSize(46, 46)
        btn_layout.addWidget(self.folder_button)

        self.cancel_button = PushButton(FIF.CLOSE, "ВІДМІНИТИ", self)
        self.cancel_button.setFixedSize(200, 46)
        self.cancel_button.hide()
        btn_layout.addWidget(self.cancel_button)

        content_layout.addLayout(btn_layout)

        content_layout.addSpacing(6)
        version_label = CaptionLabel(
            f"K5Launcher {CURRENT_VERSION} • crafted with 💜 by k5sha", self
        )
        version_label.setStyleSheet("color: #8e8e93; font-weight: 500;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(version_label)

        main_layout.addLayout(content_layout)
        main_layout.addStretch(1)
