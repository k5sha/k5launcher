from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ElevatedCardWidget,
    LineEdit,
    SwitchButton,
    TitleLabel,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF


class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("settings_interface")
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.addStretch(1)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 40, 0, 40)
        content_layout.setSpacing(20)

        title = TitleLabel("Параметри системи", self)
        content_layout.addWidget(title)

        settings_card = ElevatedCardWidget(self)
        settings_card.setFixedWidth(500)
        sc_layout = QVBoxLayout(settings_card)
        sc_layout.setContentsMargins(30, 30, 30, 30)
        sc_layout.setSpacing(20)

        theme_layout = QHBoxLayout()
        theme_layout.addWidget(BodyLabel("Темний режим", settings_card))
        theme_layout.addStretch()
        self.theme_switch = SwitchButton(parent=settings_card)
        theme_layout.addWidget(self.theme_switch)
        sc_layout.addLayout(theme_layout)

        sc_layout.addWidget(
            BodyLabel("Шлях до Java (залиште порожнім для автопошуку):", settings_card)
        )
        self.entry_java = LineEdit(settings_card)
        self.entry_java.setPlaceholderText("Автоматично")
        sc_layout.addWidget(self.entry_java)

        sc_layout.addWidget(BodyLabel("Виділення пам'яті (ГБ):", settings_card))
        self.entry_ram = LineEdit(settings_card)
        self.entry_ram.setFixedWidth(150)
        sc_layout.addWidget(self.entry_ram)

        sc_layout.addWidget(BodyLabel("Папка гри:", settings_card))
        dir_layout = QHBoxLayout()
        self.entry_dir = LineEdit(settings_card)

        self.btn_open_dir_settings = TransparentToolButton(FIF.FOLDER, settings_card)
        self.btn_open_dir_settings.setToolTip("Відкрити у Провіднику")

        dir_layout.addWidget(self.entry_dir)
        dir_layout.addWidget(self.btn_open_dir_settings)
        sc_layout.addLayout(dir_layout)

        content_layout.addWidget(settings_card)
        content_layout.addStretch()

        main_layout.addLayout(content_layout)
        main_layout.addStretch(1)
