# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Collection for Engine (The heavy part)
datas_ps, binaries_ps, hidden_ps = collect_all('playwright_stealth')

a_launcher = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_ui/update_manager.py', 'app_ui'),
        ('utils.py', '.'),
        ('dist/ghost_updater.exe', '.') 
    ],
    hiddenimports=['ctypes', 'subprocess', 'time', 'requests', 'json', 'zipfile'],
    # STRICT EXCLUSIONS to keep launcher lightweight and independent
    excludes=['flet', 'playwright', 'playwright_stealth', 'posting_engine', 'chardet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
)

a_engine = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_ui', 'app_ui'),
        ('config.yaml', '.'),
        ('groups.json', '.'),
        ('utils.py', '.'),
    ] + datas_ps, # Include all playwright_stealth data
    hiddenimports=['flet', 'playwright', 'yaml', 'json', 'requests', 'chardet'] + hidden_ps,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz_launcher = PYZ(a_launcher.pure)
pyz_engine = PYZ(a_engine.pure)

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
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)

exe_engine = EXE(
    pyz_engine,
    a_engine.scripts,
    [],
    exclude_binaries=True,
    name='AutoPostingEngine.dll', 
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)

coll = COLLECT(
    exe_launcher,
    a_launcher.binaries,
    a_launcher.datas,
    exe_engine,
    a_engine.binaries,
    a_engine.datas + binaries_ps, # Include all binaries from ps
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoPostingTool',
)
