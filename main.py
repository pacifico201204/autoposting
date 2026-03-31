import os
import flet as ft
import ssl
import sys

ssl._create_default_https_context = ssl._create_unverified_context

from utils import get_resource_path


def main(page: ft.Page):
    page.title = "Auto Posting"
    page.bgcolor = "#18191a"

    # Set window icon IMMEDIATELY before AppUI to prevent Flet icon flash
    icon_path = get_resource_path("icon.ico")
    if os.path.exists(icon_path):
        page.window.icon = icon_path

    # Reset theme_mode to string, dark mode
    page.theme_mode = "dark"
    page.padding = 0

    from app_ui import AppUI

    app = AppUI(page)
    # The UI was already added by AppUI inside itself if it doesn't return a UserControl
    # Let's just update the page.
    page.update()


if __name__ == "__main__":
    ft.run(target=main)
