import os
import flet as ft
import ssl
import sys
import builtins
from pathlib import Path

# Fix for PyInstaller: ensure exit() is available for Flet
builtins.exit = sys.exit

ssl._create_default_https_context = ssl._create_unverified_context


def cleanup_old_files():
    """Remove .old files left from previous updates"""
    try:
        # Check current exe directory and _internal
        if getattr(sys, 'frozen', False):
            app_dir = Path(os.path.dirname(sys.executable))
            targets = [app_dir, app_dir / "_internal"]
        else:
            app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            targets = [app_dir]

        for target in targets:
            if target.exists():
                for item in target.glob("*.old"):
                    try:
                        item.unlink()
                        print(f"Cleaned up: {item.name}")
                    except:
                        pass
                # Recursive cleanup for internal folders
                for item in target.rglob("*.old"):
                    try:
                        item.unlink()
                    except:
                        pass
    except:
        pass


from utils import get_resource_path


def main(page: ft.Page):
    # Cleanup old backup/update files first
    cleanup_old_files()

    page.title = "Auto Posting"
    page.bgcolor = "#18191a"

    # Set window icon IMMEDIATELY before AppUI to prevent Flet icon flash
    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        page.window.icon = icon_path

    # Reset theme_mode to string, dark mode
    page.theme_mode = "dark"
    page.padding = 0

    from app_ui.app_ui_main import AppUI

    app = AppUI(page)
    # The UI was already added by AppUI inside itself if it doesn't return a UserControl
    # Let's just update the page.
    page.update()


if __name__ == "__main__":
    ft.run(main)
