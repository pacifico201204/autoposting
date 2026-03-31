"""
Shared Utilities Module
Consolidates common functions used across multiple modules.
"""

import os
import sys


def get_resource_path(filename):
    """Get correct path for bundled resources (PyInstaller or development).

    When running as a PyInstaller bundle, resources are extracted to sys._MEIPASS.
    In development mode, resources are relative to the project root directory.

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
