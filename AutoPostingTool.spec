# -*- mode: python ; coding: utf-8 -*-
# Auto Posting Tool - Launcher & Main App Spec
# Built with PyInstaller 6+

import sys
import os

block_cipher = None

# Paths
VENV_SITE_PACKAGES = os.path.join('venv', 'Lib', 'site-packages')

# Common hidden imports and excludes
HIDDEN_IMPORTS = [
    'flet', 'flet.app', 'flet.controls', 'flet.utils', 'flet_desktop', 'flet_desktop.version',
    'playwright', 'playwright.async_api', 'playwright._impl', 'playwright._impl._api_types', 'playwright_stealth',
    'yaml', 'pyyaml', 'asyncio', 'nest_asyncio', 'PIL', 'PIL.ImageGrab', 'PIL.Image', 'requests', 'certifi',
    'urllib3', 'charset_normalizer', 'idna', 'httpx', 'httpcore', 'anyio', 'h11', 'msgpack', 'pyee', 'greenlet',
    'repath', 'oauthlib', 'posting_engine', 'storage', 'utils', 'logger_config', 'validators', 'exceptions',
    'dynamic_selector', 'anti_detection', 'detection_limiter', 'recovery_manager', 'retry_logic', 'thread_safety',
    'ui_messages', 'backup_system', 'app_ui', 'app_ui.app_ui_main', 'app_ui.ui_builder', 'app_ui.ui_handlers',
    'app_ui.ui_history', 'app_ui.ui_logging', 'app_ui.update_manager', 'app_ui.settings_manager',
    'app_ui.group_manager', 'app_ui.media_manager', 'logging.handlers', 'json', 'ssl', 'builtins', 'ctypes',
    'ctypes.util', 'tempfile', 'shutil', 'zipfile', 'pathlib', 'threading', 'typing', 're',
]

EXCLUDES = ['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'pytest', 'unittest']

# Data files (Common for both)
datas = [
    ('config.yaml', '.'),
    ('icon.ico', '.'),
    (os.path.join(VENV_SITE_PACKAGES, 'flet'), 'flet'),
    (os.path.join(VENV_SITE_PACKAGES, 'flet_desktop'), 'flet_desktop'),
    ('flet-windows.zip', os.path.join('flet_desktop', 'app')),
    (os.path.join(VENV_SITE_PACKAGES, 'playwright_stealth'), 'playwright_stealth'),
    ('app_ui', 'app_ui'),
]

# Source modules
all_py_modules = [
    'posting_engine.py', 'storage.py', 'utils.py', 'logger_config.py',
    'validators.py', 'exceptions.py', 'dynamic_selector.py', 'anti_detection.py',
    'detection_limiter.py', 'recovery_manager.py', 'retry_logic.py',
    'thread_safety.py', 'ui_messages.py', 'backup_system.py',
]
for mod in all_py_modules:
    if os.path.exists(mod):
        datas.append((mod, '.'))

# Analysis for MAIN APP
a_main = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Analysis for LAUNCHER
a_launcher = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=datas, # Sharing same datas
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    excludes=EXCLUDES,
    cipher=block_cipher,
)

pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=block_cipher)
pyz_launcher = PYZ(a_launcher.pure, a_launcher.zipped_data, cipher=block_cipher)

# EXE for Main App (to be placed in _app subfolder)
exe_main = EXE(
    pyz_main,
    a_main.scripts,
    [],
    exclude_binaries=True,
    name='AutoPostingMain',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)

# EXE for Launcher (Root level)
exe_launcher = EXE(
    pyz_launcher,
    a_launcher.scripts,
    [],
    exclude_binaries=True,
    name='AutoPostingTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe_launcher, # Target 1 (Root)
    a_launcher.binaries,
    a_launcher.zipfiles,
    a_launcher.datas,
    # Main App Binary
    exe_main,     # Target 2
    a_main.binaries,
    a_main.zipfiles,
    a_main.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoPostingTool',
)
