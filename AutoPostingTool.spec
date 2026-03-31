# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('config.yaml', '.'), ('icon.ico', '.'), ('history.json', '.'), ('C:\\Users\\lebin\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\playwright_stealth\\js', 'playwright_stealth/js')],
    hiddenimports=['app_ui', 'app_ui.app_ui_main', 'playwright_stealth', 'playwright', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

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
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoPostingTool',
)
