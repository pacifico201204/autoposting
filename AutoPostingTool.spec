# -*- mode: python ; coding: utf-8 -*-
# Auto Posting Tool - PyInstaller Config
# Optimized for structure and user-editable config files

import sys
import os

block_cipher = None

# Paths
VENV_SITE_PACKAGES = os.path.join('venv', 'Lib', 'site-packages')

all_py_modules = [
    'posting_engine.py', 'storage.py', 'utils.py', 'logger_config.py',
    'validators.py', 'exceptions.py', 'dynamic_selector.py', 'anti_detection.py',
    'detection_limiter.py', 'recovery_manager.py', 'retry_logic.py',
    'thread_safety.py', 'ui_messages.py', 'backup_system.py',
]

datas = [
    # Bundled internal resources
    ('config.yaml', '.'),
    ('icon.ico', '.'),
    (os.path.join(VENV_SITE_PACKAGES, 'flet'), 'flet'),
    (os.path.join(VENV_SITE_PACKAGES, 'flet_desktop'), 'flet_desktop'),
    ('flet-windows.zip', os.path.join('flet_desktop', 'app')),
    (os.path.join(VENV_SITE_PACKAGES, 'playwright_stealth'), 'playwright_stealth'),
    ('app_ui', 'app_ui'),
]

# Add source modules
for mod in all_py_modules:
    if os.path.exists(mod):
        datas.append((mod, '.'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'pytest', 'unittest'],
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
    name='AutoPostingTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    # Here we can add extra files to the ROOT directory by putting them in the COLLECT arguments
    # PyInstaller 6: datas in Analysis go to _internal. 
    # To place files next to EXE, we can use a small post-build hack or manual copy in my command.
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoPostingTool',
)
