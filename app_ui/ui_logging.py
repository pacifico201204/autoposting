"""Logging and log display module for AppUI"""
import os
import flet as ft
from datetime import datetime
from logger_config import log_debug, log_info, log_warning, log_error


class LogManager:
    """Quản lý hệ thống logging (fix #10: consolidate logging)"""

    def __init__(self, app_ui):
        self.app_ui = app_ui
        self.colors = app_ui.colors
        self.current_log_view = "user"
        # These will be set by AppUI after creating them
        self.log_list_user = None
        self.log_list_technical = None
        self.log_container_ref = None

    def set_lists(self, user_list, technical_list):
        """Set references to the ListViews from AppUI"""
        self.log_list_user = user_list
        self.log_list_technical = technical_list

    def log_msg(self, msg, color=None, is_technical=False):
        """
        Ghi log vào cả UI và file

        Args:
            msg: Thông báo để hiển thị
            color: Màu sắc của log item
            is_technical: Nếu True, ghi vào log_list_technical, nếu False ghi vào log_list_user
        """
        if color is None:
            color = self.colors.get("text_muted", "#B0B3B8")

        timestamp = datetime.now().strftime("%H:%M:%S")

        # Ghi vào file log theo level
        try:
            if color == self.colors.get("error"):
                log_error(msg)
            elif color == self.colors.get("success"):
                log_info(msg)
            elif color == self.colors.get("accent"):
                log_info(msg)
            else:
                log_debug(msg)
        except Exception as e:
            print(f"Logging error: {e}")

        # Determine background color based on text color
        bg_color = "transparent"
        if color == self.colors.get("error"):
            bg_color = "#33F02849"  # Nền đỏ mờ
        elif color == self.colors.get("success"):
            bg_color = "#3331A24C"  # Nền xanh lá mờ
        elif color == self.colors.get("accent"):
            bg_color = "#331877F2"  # Nền xanh dương mờ

        log_item = ft.Container(
            content=ft.Text(f"[{timestamp}] {msg}",
                            font_family="Menlo", size=12, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=bg_color
        )

        # Chèn log vào đúng list
        target_list = self.log_list_technical if is_technical else self.log_list_user
        target_list.controls.insert(0, log_item)

        # Chỉ update page nếu đang xem view tương ứng
        if (is_technical and self.current_log_view == "technical") or \
           (not is_technical and self.current_log_view == "user"):
            try:
                self.app_ui.page.update()
            except Exception as e:
                log_debug(f"Failed to update log view: {str(e)}")

    def log_msg_with_ref(self, msg, color="#FFA500", is_technical=False):
        """Tạo một log và trả về reference để dễ cập nhật"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        bg_color = "transparent"
        if color == "#FFA500":
            bg_color = "#33FFA500"  # Nền vàng mờ

        log_item = ft.Container(
            content=ft.Text(f"[{timestamp}] {msg}",
                            font_family="Menlo", size=12, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=bg_color
        )

        # Chèn log vào đúng list
        target_list = self.log_list_technical if is_technical else self.log_list_user
        target_list.controls.insert(0, log_item)

        # Update nếu đang xem view tương ứng
        if (is_technical and self.current_log_view == "technical") or \
           (not is_technical and self.current_log_view == "user"):
            try:
                self.app_ui.page.update()
            except Exception as e:
                log_debug(f"Failed to update log_msg_with_ref view: {str(e)}")

        return log_item

    def show_snack(self, message, color=None):
        """Hiển thị thông báo (SnackBar) góc dưới màn hình - cải thiện UI"""
        if color is None:
            color = self.colors.get("bg_card", "#242526")

        # Determine text color based on background
        text_color = "white" if color in [self.colors.get("error"), self.colors.get(
            "success"), self.colors.get("warning"), "#FF9800"] else "#000"

        self.app_ui.page.overlay.append(
            ft.SnackBar(
                ft.Text(message, color=text_color, size=14, weight="w500"),
                bgcolor=color,
                duration=3000,
                open=True
            )
        )
        self.app_ui.page.update()

    def switch_log_view(self, view_type, btn_user, btn_technical):
        """Chuyển giữa User Messages và Technical Logs"""
        self.current_log_view = view_type

        # Cập nhật toggle buttons style
        if view_type == "user":
            btn_user.style = ft.ButtonStyle(
                color=self.colors["accent"],
                bgcolor=self.colors["bg_card"]
            )
            btn_technical.style = ft.ButtonStyle(
                color=self.colors["text_muted"]
            )
            # Swap content container
            if self.log_container_ref:
                self.log_container_ref.content = self.log_list_user
        else:  # technical
            btn_technical.style = ft.ButtonStyle(
                color=self.colors["accent"],
                bgcolor=self.colors["bg_card"]
            )
            btn_user.style = ft.ButtonStyle(
                color=self.colors["text_muted"]
            )
            # Swap content container
            if self.log_container_ref:
                self.log_container_ref.content = self.log_list_technical

        self.app_ui.page.update()

    def export_logs(self, e):
        """Export logs thành file .txt"""
        # Tạo tên file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"logs/autposting_export_{timestamp}.txt"

        # Collect logs từ cả 2 views
        lines = []
        lines.append(
            f"=== AUTO POSTING LOGS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        lines.append(
            f"Total User Messages: {len(self.log_list_user.controls)}")
        lines.append(
            f"Total Technical Logs: {len(self.log_list_technical.controls)}\n")

        lines.append("--- USER MESSAGES ---")
        for control in reversed(self.log_list_user.controls):
            if hasattr(control, 'content') and hasattr(control.content, 'value'):
                lines.append(control.content.value)

        lines.append("\n--- TECHNICAL LOGS ---")
        for control in reversed(self.log_list_technical.controls):
            if hasattr(control, 'content') and hasattr(control.content, 'value'):
                lines.append(control.content.value)

        # Ghi vào file
        try:
            with open(export_filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            self.log_msg(
                f"✅ Exported logs: {export_filename}", color=self.colors["success"])
        except Exception as ex:
            self.log_msg(
                f"❌ Failed to export: {str(ex)}", color=self.colors["error"])
