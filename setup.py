from setuptools import setup

APP = ['main.py']
DATA_FILES = ['app_ui.py', 'storage.py']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['flet', 'playwright'],
    'iconfile': '',
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
