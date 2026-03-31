"""History management module for AppUI"""
import os
import json
import flet as ft
from datetime import datetime


class HistoryManager:
    """Quản lý lịch sử bài đăng"""

    def __init__(self, app_ui):
        self.app_ui = app_ui
        self.history_file = app_ui.config.get(
            "logging", {}).get("history_file", "history.json")
        self.max_items = app_ui.config.get(
            "logging", {}).get("max_history_items", 100)
        self.colors = app_ui.colors

    def add_to_history(self, job_data):
        """Thêm job vào lịch sử"""
        thumb_path = job_data.get("thumbnail", "")

        if thumb_path and os.path.exists(thumb_path):
            img_thumb = ft.Image(
                src=thumb_path, width=60, height=60, fit="cover", border_radius=8)
        else:
            img_thumb = ft.Container(
                width=60, height=60, bgcolor=self.colors["border"], border_radius=8)

        duration = job_data.get("duration", "N/A")
        group_name = job_data.get("group_name", "Unknown")
        post_content = job_data.get("post_content", "")[:50]

        card = ft.Container(
            content=ft.Row([
                img_thumb,
                ft.Column([
                    ft.Text(
                        group_name, color=self.colors["text_main"], size=13),
                    ft.Text(
                        f"{duration}s | {post_content}...",
                        color=self.colors["text_muted"], size=12
                    )
                ], expand=True, spacing=4)
            ], spacing=15, vertical_alignment="center"),
            bgcolor=self.colors["bg_card"],
            border_radius=12,
            padding=15,
            border=ft.border.all(1, self.colors["border"]),
            margin=ft.margin.only(bottom=10),
            data=job_data
        )

        # Limit history to MAX_HISTORY_ITEMS
        if len(self.app_ui.history_list_view.controls) >= self.max_items:
            self.app_ui.history_list_view.controls.pop(0)

        self.app_ui.history_list_view.controls.insert(0, card)

        # Auto-save history to file
        self.save_to_file()

        try:
            self.app_ui.history_list_view.update()
        except Exception as e:
            self.app_ui.log_msg(
                f"⚠️ Lỗi cập nhật lịch sử UI: {str(e)[:50]}", is_technical=True)

    def clear(self, e):
        """Xóa tất cả lịch sử"""
        import shutil

        # Xóa tất cả các item trong history UI
        self.app_ui.history_list_view.controls.clear()
        self.app_ui.page.update()

        # Xóa các file ảnh tạm
        err_dir = os.path.join(os.getcwd(), "error_screenshots")
        if os.path.exists(err_dir):
            try:
                shutil.rmtree(err_dir)
                self.app_ui.log_msg("Đã xóa tất cả ảnh lỗi tạm thời.",
                                    color=self.colors["success"])
            except Exception as e:
                self.app_ui.log_msg(
                    f"Lỗi khi xóa ảnh lỗi tạm thời: {str(e)}", color=self.colors["error"])

        # Xóa file lịch sử
        self.delete_file()

    def save_to_file(self):
        """Lưu lịch sử vào file JSON (fix #9: persistent history)"""
        try:
            history_data = []
            for item in self.app_ui.history_list_view.controls:
                if hasattr(item, 'data') and item.data:
                    history_data.append(item.data)

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.app_ui.log_msg(
                f"⚠️ Lỗi lưu lịch sử: {str(e)[:50]}", is_technical=True)

    def load_from_file(self):
        """Tải lịch sử từ file JSON on app startup (fix #9)"""
        try:
            if not os.path.exists(self.history_file):
                return

            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            # Rebuild history UI from saved data
            for item_data in history_data[:self.max_items]:
                thumb_path = item_data.get("thumbnail", "")
                if thumb_path and os.path.exists(thumb_path):
                    img_thumb = ft.Image(
                        src=thumb_path, width=60, height=60, fit="cover", border_radius=8)
                else:
                    img_thumb = ft.Container(
                        width=60, height=60, bgcolor=self.colors["border"], border_radius=8)

                card = ft.Container(
                    content=ft.Row([
                        img_thumb,
                        ft.Column([
                            ft.Text("Lịch sử bài đăng",
                                    color=self.colors["text_main"], size=13),
                            ft.Text(
                                f"Tải từ file", color=self.colors["text_muted"], size=12, italic=True)
                        ], expand=True, spacing=4)
                    ], spacing=15, vertical_alignment="center"),
                    bgcolor=self.colors["bg_card"],
                    border_radius=12,
                    padding=15,
                    border=ft.border.all(1, self.colors["border"]),
                    margin=ft.margin.only(bottom=10),
                    data=item_data
                )
                self.app_ui.history_list_view.controls.append(card)

            if history_data:
                self.app_ui.log_msg(
                    f"✓ Đã tải {len(history_data[:self.max_items])} mục từ lịch sử", is_technical=True)
        except Exception as e:
            self.app_ui.log_msg(
                f"⚠️ Lỗi tải lịch sử: {str(e)[:50]}", is_technical=True)

    def delete_file(self):
        """Xóa file lịch sử"""
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
        except Exception as e:
            self.app_ui.log_msg(
                f"⚠️ Lỗi xóa file lịch sử: {str(e)[:50]}", is_technical=True)
