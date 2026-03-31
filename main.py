import os
import flet as ft
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


def main(page: ft.Page):
    page.title = "Auto Posting"
    page.bgcolor = "#18191a"

    # Reset theme_mode to string, dark mode
    page.theme_mode = "dark"
    page.padding = 0

    from app_ui import AppUI

    app = AppUI(page)
    # The UI was already added by AppUI inside itself if it doesn't return a UserControl
    # Let's just update the page.
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
