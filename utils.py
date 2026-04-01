"""
Shared Utilities Module
Consolidates common functions used across multiple modules.
"""

import os
import sys


def get_resource_path(filename):
    """Get correct path for bundled READ-ONLY resources (PyInstaller or development).

    When running as a PyInstaller bundle, resources are extracted to sys._MEIPASS.
    In development mode, resources are relative to the project root directory.

    Use this for: icon.ico, config.yaml (template only)
    Do NOT use for writable files like groups.json, history.json, logs/

    Args:
        filename: Name of the resource file (e.g., 'icon.ico', 'config.yaml')

    Returns:
        Absolute path to the resource file
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundled EXE
        base_path = sys._MEIPASS
    else:
        # Running in development mode - always use project root
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


def get_app_dir():
    """Get the application working directory for writable files.

    When frozen (PyInstaller): directory containing the .exe
    When development: project root directory

    Returns:
        Absolute path to the writable app directory
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundled EXE - use exe's directory
        return os.path.dirname(sys.executable)
    else:
        # Running in development mode
        return os.path.dirname(os.path.abspath(__file__))


def get_writable_path(filename):
    """Get path for writable files (data, config, logs).

    Unlike get_resource_path, this returns a path in the app directory
    (next to the .exe) which is writable, not in the read-only _MEIPASS.

    Use this for: groups.json, history.json, config.yaml (user copy), logs/

    Args:
        filename: Name of the file (e.g., 'groups.json', 'history.json')

    Returns:
        Absolute path to the writable file location
    """
    return os.path.join(get_app_dir(), filename)
