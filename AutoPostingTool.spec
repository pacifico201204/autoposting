# -*- mode: python ; coding: utf-8 -*-
# Auto Posting Tool - PyInstaller Config
# One-Dir Mode Only (simpler to update and distribute)

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include Flet data files
        (os.path.join(sys.base_prefix, 'Lib', 'site-packages', 'flet'), 'flet'),
        # Include Playwright stealth files  
        (os.path.join(sys.base_prefix, 'Lib', 'site-packages', 'playwright_stealth'), 'playwright_stealth'),
        # Include config template
        ('config.yaml', '.'),
        # Include application icon
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'playwright_stealth',
        'playwright',
        'flet',
        'yaml',
        'asyncio',
        'playwright.async_api',
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
    name='AutoPostingTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)

# One-Dir Distribution
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoPostingTool',
)
