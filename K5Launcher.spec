# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'), 
    ],
    hiddenimports=[
        'src.config.settings',
        'src.core.java',
        'src.core.versions',
        'src.core.downloader',
        'src.core.launcher',
        'src.ui.signals',
        'src.ui.app',
        'src.ui.views.home_view',
        'src.ui.views.settings_view',
        'src.utils.helpers',
        'src.utils.updater',
        'qfluentwidgets',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='K5Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='K5Launcher',
)