from exceptions import TooManyPostsException, ContextDestroyedException
from detection_limiter import DetectionLimiter
from validators import Validators, ValidationError
from ui_messages import get_message, get_message_color
from dynamic_selector import DynamicSelector
from logger_config import log_debug, log_info, log_warning, log_error, log_exception
from playwright.async_api import async_playwright
from storage import load_groups, save_groups
from app_ui.ui_history import HistoryManager
from app_ui.ui_logging import LogManager
import urllib.parse
import flet as ft
import os
import asyncio
import threading
import json
from datetime import datetime
from PIL import ImageGrab
import yaml

# Import Playwright Stealth (chính xác)
from playwright_stealth import Stealth

import nest_asyncio
nest_asyncio.apply()

# Load configuration from config.yaml


def load_config(config_file="config.yaml"):
    """Load configuration from YAML file"""
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")

    # Return default config if file not found
    return {
        "window": {"width": 1400, "height": 850},
        "delays": {"post_min": 5, "post_max": 10},
        "logging": {"history_file": "history.json", "max_history_items": 100},
        "ui": {"font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"}
    }


# Import logger & dynamic selector

# Import validators and detection limiter

# Bộ màu sắc Facebook Night Mode (Dark Web chuẩn)
COLORS = {
    "bg_main": "#18191A",       # Nền trang web (Facebook Night Mode)
    "bg_card": "#242526",       # Nền các Card/Bảng
    "border": "#3E4042",        # Viền mờ ngăn cách
    "accent": "#1877F2",        # Facebook Blue đặc trưng
    "text_main": "#E4E6EB",     # Chữ chính sáng
    "text_muted": "#B0B3B8",    # Chữ mờ / Chữ phụ
    "error": "#F02849",         # Đỏ cảnh báo / Xoá
    "success": "#31A24C",       # Xanh lá thành công / Online
    "warning": "#F5A623"        # Vàng cảnh báo
}

# Load config from file
CONFIG = load_config()

# Get values from config
FONT_FAMILY = CONFIG.get("ui", {}).get(
    "font_family", "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif")
HISTORY_FILE = CONFIG.get("logging", {}).get("history_file", "history.json")
MAX_HISTORY_ITEMS = CONFIG.get("logging", {}).get("max_history_items", 100)


class AppUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config = CONFIG  # Store config for helper classes
        self.colors = COLORS  # Store colors for helper classes
        self.groups_data = load_groups()
        self.image_paths = []  # Danh sách ảnh chờ đăng
        self.is_running = False

        # Load delays from config
        delays_config = CONFIG.get("delays", {})
        self.post_delay_min = delays_config.get("post_min", 5)
        self.post_delay_max = delays_config.get("post_max", 10)

        self.is_all_selected = False  # Trạng thái chọn tất cả
        self.job_history = []  # Lưu danh sách các job

        # Initialize detection limiter (Vấn đề 1: Anti-detection)
        self.detection_limiter = DetectionLimiter()

        # Initialize helper managers for modular code
        self.history_manager = HistoryManager(self)
        self.log_manager = LogManager(self)

        self.setup_page()
        self.build_ui()
        self.populate_groups()

        # Show "Bot ready" message after initialization
        self.log_msg(get_message("bot_ready"), color=COLORS["accent"])

    def setup_page(self):
        """Cấu hình cửa sổ Flet App"""
        self.page.title = "Auto Posting"
        self.page.window.icon = "icon.ico"  # Set window icon
        # Changed enum to string "dark" (already handled by Flet theme correctly but just in case)
        self.page.theme_mode = "dark"
        self.page.bgcolor = COLORS["bg_main"]
        self.page.fonts = {"FacebookFont": FONT_FAMILY}
        self.page.theme = ft.Theme(font_family="FacebookFont")
        self.page.padding = 0  # Bỏ padding trang để làm layout full màn hình
        self.page.scroll = "adaptive"

        # Load window size from config
        window_config = CONFIG.get("window", {})
        self.page.window.width = window_config.get("width", 1400)
        self.page.window.height = window_config.get("height", 850)

        # Bắt sự kiện thả file vào trang
        self.page.on_drop = self.on_file_drop

    def on_file_drop(self, e: ft.FilePickerUploadEvent):
        """Xử lý kéo thả file trực tiếp vào giao diện (Finder -> Flet)"""
        # Nếu Flet version cũ/mới truyền `e` có files hoặc event chứa thông tin
        if hasattr(e, "files") and e.files:
            # FilePicker result
            paths = [file.path for file in e.files]
        elif hasattr(e, "data") and e.data:
            # DropEvent
            import json
            try:
                data = json.loads(e.data)
                if isinstance(data, list):
                    paths = [item.get("src") or item.get("path")
                             for item in data]
                else:
                    paths = []
            except Exception as e:
                self.log_msg(
                    f"⚠️ Lỗi parse drop event: {str(e)[:50]}", is_technical=True)
                paths = []
        else:
            paths = []

        added_count = 0
        for p in paths:
            if not p:
                continue
            # Xử lý URI/Path
            p = urllib.parse.unquote(p.replace("file://", ""))
            if os.path.isfile(p) and p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                if p not in self.image_paths:
                    self.image_paths.append(p)
                    added_count += 1

        if added_count > 0:
            self.log_msg(
                f"Đã thêm {added_count} ảnh từ Kéo Thả.", color=COLORS["accent"])
            self.render_album_slots()
            self.page.update()

    def make_card(self, title, content, expand=False, padding=15):
        """Hàm dựng các hộp nội dung (Cards) nhất quán"""
        container = ft.Container(
            content=ft.Column([
                ft.Text(title, weight="bold", size=16,
                        color=COLORS["text_main"]),
                ft.Divider(color=COLORS["border"], height=1),
                content
            ], spacing=15, expand=expand),
            padding=padding,
            bgcolor=COLORS["bg_card"],
            border_radius=12,
            border=ft.Border.all(
                1, COLORS["border"]) if COLORS["border"] else None,
            expand=expand,
            margin=ft.margin.only(bottom=15)
        )
        return container

    def build_ui(self):
        """Xây dựng và Lắp ráp Giao diện UI: LAYOUT 3 CỘT FACEBOOK NIGHT MODE"""

        # --- HEADER (Thanh điều hướng trên cùng giả lập Facebook) ---
        header = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.FACEBOOK,
                            color=COLORS["accent"], size=40),
                    ft.Text("Auto Posting by Tristan", size=24,
                            weight="w800", color=COLORS["text_main"])
                ], spacing=10),
                ft.Container(expand=True),  # Khoảng trống giữa
                # Đã bỏ các icon ở góc phải theo yêu cầu
            ], alignment="spaceBetween", vertical_alignment="center"),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=COLORS["bg_card"],
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border"]))
        )

        # ================= CỘT TRÁI (MENU & CÔNG CỤ) - Chiếm khoảng 20% =================
        menu_items = ft.Column([
            self.make_menu_item(ft.Icons.ROCKET_LAUNCH,
                                "Start Auto", COLORS["accent"], self.start_auto),
            self.make_menu_item(ft.Icons.STOP_CIRCLE, "Stop",
                                COLORS["error"], self.stop_auto),
            ft.Divider(color=COLORS["border"]),
            self.make_menu_item(ft.Icons.GROUP_ADD, "Add Group",
                                COLORS["success"], self.open_add_group_dialog),
            self.make_menu_item(ft.Icons.SETTINGS, "Delay",
                                COLORS["text_main"], self.open_settings_dialog),
            self.make_menu_item(ft.Icons.HISTORY, "History",
                                COLORS["text_main"], self.toggle_history_view),
        ], spacing=5)

        col_left = ft.Container(
            content=menu_items,
            padding=20,
            expand=2
        )

        # ================= CỘT GIỮA (SOẠN THẢO BÀI ĐĂNG) - Chiếm khoảng 50% =================

        # 1. Soạn thảo văn bản
        self.text_content = ft.TextField(
            multiline=True,
            min_lines=12, max_lines=20,
            expand=True,
            hint_text="Enter post content here...",
            border_color="transparent",  # Kiểu không viền giống Facebook
            focused_border_color="transparent",
            bgcolor=COLORS["bg_card"],
            text_size=16,
            color=COLORS["text_main"],
            cursor_color=COLORS["accent"],
            height=300
        )
        card_content = self.make_card("Create Post", ft.Column(
            [self.text_content], expand=True), expand=False)

        # 2. Album ảnh (BỎ DRAG DROP -> BUTTON PASTE)
        self.btn_paste_image = ft.ElevatedButton(
            "PASTE IMAGE FROM CLIPBOARD",
            icon=ft.Icons.CONTENT_PASTE,
            color="#ffffff",
            bgcolor="#1877F2",  # Facebook Blue
            on_click=self.paste_image_from_clipboard,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=20, vertical=15),
            ),
            height=50,
            expand=True,
        )

        self.attachment_list_container = ft.Column(spacing=5)

        album_controls = ft.Column(
            [
                # Bọc trong row để expand=True có tác dụng ngang
                ft.Row([self.btn_paste_image], expand=True),
                self.attachment_list_container,
            ],
            spacing=15,
        )
        self.render_album_slots()

        card_image = self.make_card(
            "Attached Media", album_controls, expand=False)

        self.post_compose_col = ft.Column(
            [card_content, card_image], scroll="adaptive", expand=True)

        # ----------------- TRANG POST HISTORY -----------------
        self.history_list_view = ft.ListView(
            expand=True, spacing=10, auto_scroll=False)

        btn_back_home = ft.ElevatedButton(
            "Back to Dashboard",
            icon=ft.Icons.ARROW_BACK,
            bgcolor=COLORS["border"],
            color=COLORS["text_main"],
            on_click=self.toggle_history_view
        )

        history_header = ft.Row([
            ft.Text("Post History", size=20, weight="bold",
                    color=COLORS["text_main"]),
            btn_back_home
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.post_history_col = ft.Column([
            history_header,
            ft.Divider(color=COLORS["border"]),
            self.history_list_view
        ], expand=True, visible=False)

        col_center = ft.Container(
            content=ft.Stack([
                self.post_compose_col,
                self.post_history_col
            ], expand=True),
            padding=ft.padding.only(top=20, left=10, right=10, bottom=20),
            expand=5
        )

        # ================= CỘT PHẢI (QUẢN LÝ NHÓM & LOGS) - Chiếm khoảng 30% =================

        # 1. Quản lý nhóm (Bảng rút gọn)
        # Nút "ALL" thay cho Checkbox
        self.btn_select_all = ft.ElevatedButton(
            "ALL",
            on_click=self.toggle_select_all_groups,
            color=COLORS["text_main"],
            bgcolor=COLORS["border"],  # Trạng thái chưa chọn
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=20),
                padding=ft.padding.symmetric(horizontal=15, vertical=0),
            ),
            height=30
        )

        self.table_groups = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Row([
                        self.btn_select_all,
                    ], alignment="start")
                ),
            ],
            rows=[],
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=40,
            show_checkbox_column=False,
            heading_row_color="transparent",
            expand=True  # fit with bounding box
        )

        card_groups = self.make_card("Groups List", ft.Container(
            content=ft.Column([self.table_groups], scroll="auto", expand=True),
            border_radius=8, bgcolor=COLORS["bg_card"],
            expand=True
        ), expand=True)

        # Dialog thêm nhóm
        self.add_name_input = ft.TextField(
            label="Group Name", border_color=COLORS["border"], color=COLORS["text_main"])
        self.add_url_input = ft.TextField(
            label="Group URL", border_color=COLORS["border"], color=COLORS["text_main"])
        self.add_dialog = ft.AlertDialog(
            title=ft.Text("Add New Group", color=COLORS["text_main"]),
            bgcolor=COLORS["bg_card"],
            content=ft.Column(
                [self.add_name_input, self.add_url_input], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=self.close_add_dialog,
                              style=ft.ButtonStyle(color=COLORS["text_muted"])),
                ft.TextButton("Save", on_click=self.confirm_add_group,
                              style=ft.ButtonStyle(color=COLORS["accent"]))
            ]
        )

        # Dialog Cài đặt Delay
        self.delay_min_input = ft.TextField(
            label="From (seconds)",
            value=str(self.post_delay_min),
            border_color=COLORS["border"],
            color=COLORS["text_main"],
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120
        )
        self.delay_max_input = ft.TextField(
            label="To (seconds)",
            value=str(self.post_delay_max),
            border_color=COLORS["border"],
            color=COLORS["text_main"],
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120
        )
        self.settings_dialog = ft.AlertDialog(
            title=ft.Text("Random Delay Settings", color=COLORS["text_main"]),
            bgcolor=COLORS["bg_card"],
            content=ft.Column([
                ft.Row([self.delay_min_input, ft.Text(
                    "-", color=COLORS["text_main"]), self.delay_max_input]),
                ft.Text("Random wait time between posts (seconds)",
                        color=COLORS["text_muted"], size=12)
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=self.close_settings_dialog,
                              style=ft.ButtonStyle(color=COLORS["text_muted"])),
                ft.TextButton("Save", on_click=self.confirm_settings,
                              style=ft.ButtonStyle(color=COLORS["accent"]))
            ]
        )

        # 2. Log Console with Toggle (User Messages vs Technical Logs)
        self.log_list_user = ft.ListView(
            expand=True, auto_scroll=False, spacing=5)  # User-friendly messages
        self.log_list_technical = ft.ListView(
            expand=True, auto_scroll=False, spacing=5)  # Technical details
        self.current_log_view = "user"  # Trạng thái hiện tại: "user" hoặc "technical"

        # Pass log lists to log manager (Issue #7: modular code)
        self.log_manager.set_lists(self.log_list_user, self.log_list_technical)

        # Toggle buttons
        btn_user_messages = ft.TextButton(
            "User Messages",
            on_click=lambda e: self.switch_log_view(
                "user", btn_user_messages, btn_technical_logs)
        )
        btn_technical_logs = ft.TextButton(
            "Technical Logs",
            on_click=lambda e: self.switch_log_view(
                "technical", btn_user_messages, btn_technical_logs)
        )

        # Lưu reference cho toggle buttons
        self.btn_user_messages = btn_user_messages
        self.btn_technical_logs = btn_technical_logs

        # Toggle buttons row styling
        toggle_row = ft.Container(
            content=ft.Row([
                ft.Text("Logs:", size=13, weight="bold",
                        color=COLORS["text_main"]),
                btn_user_messages,
                btn_technical_logs,
                ft.Container(expand=True),  # Spacer
                ft.IconButton(
                    ft.Icons.FILE_DOWNLOAD_OUTLINED,
                    tooltip="Export logs",
                    on_click=self.export_logs,
                    icon_color=COLORS["text_muted"],
                    icon_size=18
                )
            ], alignment="start", vertical_alignment="center", spacing=8),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border_radius=ft.border_radius.vertical(top=8),
            bgcolor=COLORS["bg_card"],
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border"]))
        )

        log_container = ft.Container(
            content=self.log_list_user, expand=True, padding=10,
            border_radius=ft.border_radius.vertical(bottom=8),
            bgcolor=COLORS["bg_main"]  # Nền đen sâu cho log
        )
        self.log_container_ref = log_container  # Lưu reference để switch_log_view dùng

        card_logs = self.make_card(
            "Activity Logs",
            ft.Column([
                toggle_row,
                log_container
            ], expand=True, spacing=0),
            padding=0,
            expand=True
        )

        col_right = ft.Container(
            content=ft.Column([card_groups, card_logs], expand=True),
            padding=ft.padding.only(top=20, left=10, right=20, bottom=20),
            expand=3
        )

        # ================= GHÉP TOÀN BỘ LAYOUT LẠI =================
        # Chỉ dùng để track state, nút thật ở menu
        self.btn_start = ft.FilledButton("Bắt đầu")
        self.btn_stop = ft.Button("Dừng", disabled=True)

        main_layout = ft.Row([
            col_left,
            col_center,
            col_right
        ], expand=True, alignment="start", vertical_alignment="start")

        self.page.add(
            ft.Column([
                header,
                main_layout
            ], expand=True, spacing=0)
        )
        self.page.overlay.append(self.add_dialog)
        self.page.overlay.append(self.settings_dialog)

        # Fix #9: Load history from persistent file on startup
        self.history_manager.load_from_file()

        self.page.update()

    def make_menu_item(self, icon, text, color, on_click):
        """Tạo nút menu bên trái phong cách Facebook"""
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=28),
                ft.Text(text, size=15, weight="w500",
                        color=COLORS["text_main"])
            ], spacing=15, expand=True),  # Expand the row so it captures clicks everywhere inside
            padding=10,
            border_radius=8,
            on_click=on_click,
            ink=True,
            on_hover=self.on_menu_hover
        )

    def on_menu_hover(self, e):
        e.control.bgcolor = COLORS["bg_card"] if e.data == "true" else "transparent"
        e.control.update()

    def toggle_history_view(self, e):
        """Chuyển đổi qua lại giữa màn hình Soạn bài và Lịch sử"""
        is_history_visible = not self.post_history_col.visible
        self.post_history_col.visible = is_history_visible
        self.post_compose_col.visible = not is_history_visible
        self.page.update()

    def add_to_history(self, job_data):
        import os
        job_id = job_data.get("id", "N/A")
        time_str = job_data.get("time", "")
        content = job_data.get("content", "Không có nội dung")
        thumb_path = job_data.get("thumbnail")
        groups = job_data.get("groups", [])
        status = job_data.get("status", "Running")

        status_color = "#33FFA500"  # Vàng (Running)
        text_color = "#FFA500"
        if status == "Success":
            status_color = "#3331A24C"
            text_color = COLORS["success"]
        elif status == "Failed":
            status_color = "#33F02849"
            text_color = COLORS["error"]

        status_badge = ft.Container(
            content=ft.Text(status, color=text_color, size=12, weight="bold"),
            bgcolor=status_color,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            border_radius=12
        )

        if thumb_path and os.path.exists(thumb_path):
            img_thumb = ft.Image(src=thumb_path, width=60,
                                 height=60, fit="cover", border_radius=8)
        else:
            img_thumb = ft.Container(
                content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED,
                                color=COLORS["text_muted"], size=30),
                width=60, height=60, bgcolor=COLORS["border"], border_radius=8, alignment=ft.alignment.center
            )

        groups_text = ", ".join(groups) if groups else "Không có nhóm"

        card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(
                        f"Job #{job_id}", color=COLORS["text_main"], weight="bold", size=14),
                    ft.Text(f"| {time_str}",
                            color=COLORS["text_muted"], size=12),
                    ft.Container(expand=True),
                    status_badge
                ], alignment="spaceBetween"),
                ft.Row([
                    img_thumb,
                    ft.Column([
                        ft.Text(content[:60] + "..." if len(content) >
                                60 else content, color=COLORS["text_main"], size=13),
                        ft.Text(f"Nhóm: {groups_text[:70]}..." if len(
                            groups_text) > 70 else f"Nhóm: {groups_text}", color=COLORS["text_muted"], size=12, italic=True)
                    ], expand=True, spacing=4)
                ], spacing=15, vertical_alignment="center")
            ], spacing=8),
            bgcolor=COLORS["bg_card"],
            border_radius=12,
            padding=15,
            border=ft.border.all(1, COLORS["border"]),
            margin=ft.margin.only(bottom=10),
            data={"thumbnail": thumb_path}
        )

        self.history_list_view.controls.insert(0, card)

        # Fix #8: Giới hạn lịch sử UI (tăng từ 10 → 100 items để tránh memory leak)
        if len(self.history_list_view.controls) > MAX_HISTORY_ITEMS:
            oldest_card = self.history_list_view.controls.pop()

            # Xóa file ảnh tạm trong ổ cứng
            old_thumb = oldest_card.data.get("thumbnail")
            if old_thumb and "temp_images" in old_thumb:
                try:
                    if os.path.exists(old_thumb):
                        os.remove(old_thumb)
                except Exception as e:
                    self.log_msg(
                        f"⚠️ Không thể xóa ảnh tạm: {str(e)[:50]}", is_technical=True)

        # Auto-save history to file (fix #9: persistent history)
        self.save_history_to_file()

        try:
            self.history_list_view.update()
        except Exception as e:
            self.log_msg(
                f"⚠️ Lỗi cập nhật lịch sử UI: {str(e)[:50]}", is_technical=True)

    def clear_history(self, e):
        # Dọn dẹp tất cả khi người dùng nhấn xóa lịch sử
        import os
        # Xóa tất cả các item trong history UI
        self.history_list_view.controls.clear()
        self.page.update()

        # Xóa các file ảnh tạm nếu có
        err_dir = os.path.join(os.getcwd(), "error_screenshots")
        if os.path.exists(err_dir):
            import shutil
            try:
                shutil.rmtree(err_dir)
                self.log_msg("Đã xóa tất cả ảnh lỗi tạm thời.",
                             color=COLORS["success"])
            except Exception as e:
                self.log_msg(
                    f"Lỗi khi xóa ảnh lỗi tạm thời: {str(e)}", color=COLORS["error"])

        # Also delete history file
        self.delete_history_file()

    def save_history_to_file(self):
        """Lưu lịch sử vào file JSON (fix #9: persistent history)"""
        try:
            history_data = []
            for item in self.history_list_view.controls:
                if hasattr(item, 'data') and item.data:
                    history_data.append(item.data)

            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_msg(
                f"⚠️ Lỗi lưu lịch sử: {str(e)[:50]}", is_technical=True)

    def load_history_from_file(self):
        """Tải lịch sử từ file JSON on app startup (fix #9)"""
        try:
            if not os.path.exists(HISTORY_FILE):
                return

            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            # Rebuild history UI from saved data (limit to MAX_HISTORY_ITEMS)
            for item_data in history_data[:MAX_HISTORY_ITEMS]:
                thumb_path = item_data.get("thumbnail", "")
                if thumb_path and os.path.exists(thumb_path):
                    img_thumb = ft.Image(
                        src=thumb_path, width=60, height=60, fit="cover", border_radius=8)
                else:
                    img_thumb = ft.Container(
                        width=60, height=60, bgcolor=COLORS["border"], border_radius=8)

                card = ft.Container(
                    content=ft.Row([
                        img_thumb,
                        ft.Column([
                            ft.Text("Lịch sử bài đăng",
                                    color=COLORS["text_main"], size=13),
                            ft.Text(
                                f"Tải từ file", color=COLORS["text_muted"], size=12, italic=True)
                        ], expand=True, spacing=4)
                    ], spacing=15, vertical_alignment="center"),
                    bgcolor=COLORS["bg_card"],
                    border_radius=12,
                    padding=15,
                    border=ft.border.all(1, COLORS["border"]),
                    margin=ft.margin.only(bottom=10),
                    data=item_data
                )
                self.history_list_view.controls.append(card)

            if history_data:
                self.log_msg(
                    f"✓ Đã tải {len(history_data[:MAX_HISTORY_ITEMS])} mục từ lịch sử", is_technical=True)
        except Exception as e:
            self.log_msg(
                f"⚠️ Lỗi tải lịch sử: {str(e)[:50]}", is_technical=True)

    def delete_history_file(self):
        """Xóa file lịch sử (khi người dùng bấm clear)"""
        try:
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
        except Exception as e:
            self.log_msg(
                f"⚠️ Lỗi xóa file lịch sử: {str(e)[:50]}", is_technical=True)

    def log_msg(self, msg, color=COLORS["text_muted"], is_technical=False):
        """
        Ghi log vào cả UI và file

        Args:
            msg: Thông báo để hiển thị (Vietnamese user message hoặc technical detail)
            color: Màu sắc của log item
            is_technical: Nếu True, ghi vào log_list_technical. Nếu False, ghi vào log_list_user
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Ghi vào file log theo level
        try:
            if color == COLORS["error"]:
                log_error(msg)
            elif color == COLORS["success"]:
                log_info(msg)
            elif color == COLORS["accent"]:
                log_info(msg)
            else:
                log_debug(msg)
        except Exception as e:
            print(f"Logging error: {e}")

        # Determine background color based on text color
        bg_color = "transparent"
        if color == COLORS["error"]:
            bg_color = "#33F02849"  # Nền đỏ mờ
        elif color == COLORS["success"]:
            bg_color = "#3331A24C"  # Nền xanh lá mờ
        elif color == COLORS["accent"]:
            bg_color = "#331877F2"  # Nền xanh dương mờ

        log_item = ft.Container(
            content=ft.Text(f"[{timestamp}] {msg}",
                            font_family="Menlo", size=12, color=color),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=bg_color
        )

        # Chèn log vào đúng list (user hoặc technical)
        target_list = self.log_list_technical if is_technical else self.log_list_user
        target_list.controls.insert(0, log_item)

        # Chỉ update page nếu đang xem view tương ứng
        if (is_technical and self.current_log_view == "technical") or \
           (not is_technical and self.current_log_view == "user"):
            self.page.update()

    def log_msg_with_ref(self, msg, color="#FFA500", is_technical=False):
        """Tạo một log và trả về reference Container để dễ cập nhật, dùng cho Countdown."""
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

        # Chỉ update page nếu đang xem view tương ứng
        if (is_technical and self.current_log_view == "technical") or \
           (not is_technical and self.current_log_view == "user"):
            self.page.update()

        return log_item

    def show_snack(self, message, color=COLORS["text_main"]):
        """Hiển thị thông báo (SnackBar) góc dưới màn hình"""
        self.page.overlay.append(
            ft.SnackBar(
                ft.Text(message, color="white"),
                bgcolor=color,
                open=True
            )
        )
        self.page.update()

    def switch_log_view(self, view_type, btn_user, btn_technical):
        """Chuyển giữa User Messages và Technical Logs"""
        self.current_log_view = view_type

        # Cập nhật toggle buttons style
        if view_type == "user":
            btn_user.style = ft.ButtonStyle(
                color=COLORS["accent"],
                bgcolor=COLORS["bg_card"]
            )
            btn_technical.style = ft.ButtonStyle(
                color=COLORS["text_muted"]
            )
            # Swap content container
            log_container = self.find_log_container()
            if log_container:
                log_container.content = self.log_list_user
        else:  # technical
            btn_technical.style = ft.ButtonStyle(
                color=COLORS["accent"],
                bgcolor=COLORS["bg_card"]
            )
            btn_user.style = ft.ButtonStyle(
                color=COLORS["text_muted"]
            )
            # Swap content container
            log_container = self.find_log_container()
            if log_container:
                log_container.content = self.log_list_technical

        self.page.update()

    def find_log_container(self):
        """Tìm Container chứa log list (hỗ trợ cho switch_log_view)"""
        # Tạo reference khi build_ui nếu cần
        if hasattr(self, 'log_container_ref'):
            return self.log_container_ref
        return None

    def export_logs(self, e):
        """Export logs thành file .txt"""
        from datetime import datetime

        # Tạo tên file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"logs/vibecode_export_{timestamp}.txt"

        # Collect logs từ cả 2 views
        lines = []
        lines.append(
            f"=== VIBECODE AUTO LOGS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
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
                f"✅ Exported logs: {export_filename}", color=COLORS["success"])
        except Exception as ex:
            self.log_msg(
                f"❌ Failed to export: {str(ex)}", color=COLORS["error"])

    def render_album_slots(self):
        """Cập nhật phần tử danh sách hiển thị tên ảnh và preview thu nhỏ."""
        if not hasattr(self, 'attachment_list_container'):
            return

        self.attachment_list_container.controls.clear()

        if not self.image_paths:
            self.attachment_list_container.controls.append(
                ft.Text("No images attached.",
                        color=COLORS["text_muted"], italic=True)
            )
        else:
            count = len(self.image_paths)

            header_row = ft.Row([
                ft.Text(f"Attached {count} images:",
                        weight="bold", color=COLORS["success"]),
                ft.TextButton("Clear All", icon=ft.Icons.DELETE,
                              icon_color=COLORS["error"], on_click=lambda e: self.clear_all_images())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            self.attachment_list_container.controls.append(header_row)

            import os
            for idx, path in enumerate(self.image_paths):
                filename = os.path.basename(path)

                # Create thumbnail preview
                try:
                    thumbnail = ft.Image(
                        src=path,
                        width=70,
                        height=70,
                        fit="cover",
                        border_radius=6
                    )
                except:
                    # Fallback if image fails to load
                    thumbnail = ft.Container(
                        content=ft.Icon(
                            ft.Icons.IMAGE, color=COLORS["text_muted"], size=35),
                        width=70,
                        height=70,
                        bgcolor=COLORS["border"],
                        border_radius=6,
                        alignment=ft.alignment.center
                    )

                item_row = ft.Container(
                    content=ft.Row([
                        thumbnail,
                        ft.Column([
                            ft.Text(
                                filename, size=12, color=COLORS["text_main"], weight="bold", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"Image {idx + 1}", size=10,
                                    color=COLORS["text_muted"], italic=True)
                        ], expand=True, spacing=4),
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=18,
                                      icon_color=COLORS["error"], on_click=self.create_remove_image_handler(idx))
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=8,
                    border=ft.Border.all(1, COLORS["border"]),
                    border_radius=8,
                    bgcolor=COLORS["bg_main"]
                )
                self.attachment_list_container.controls.append(item_row)

        # Gọi page.update() an toàn
        if getattr(self, "page", None):
            self.page.update()

    def clear_all_images(self):
        self.image_paths.clear()
        self.render_album_slots()
        self.log_msg("All images cleared.")

    def create_remove_image_handler(self, idx):
        return lambda e: self.remove_image_at(idx)

    def remove_image_at(self, idx):
        if 0 <= idx < len(self.image_paths):
            removed = self.image_paths.pop(idx)
            self.log_msg(f"Image removed: {os.path.basename(removed)}")
            self.render_album_slots()

    def on_drag_hover(self, e):
        """Hover hint khi kéo vật phẩm qua (Hiệu ứng)"""
        pass

    def on_image_path_submitted(self, e):
        """Nhận đường dẫn (kể cả kéo thả text path vào đây)"""
        path = self.image_path_input.value.strip()

        # Có thể người dùng kéo thả nhiều file ra chuỗi cách nhau khoảng trắng hoặc newline
        paths = [p.strip().replace("file://", "")
                 for p in path.split('\n') if p.strip()]
        if not paths:
            paths = [path]  # fall back

        added_count = 0
        for p in paths:
            # Decode URL enconded characters if any
            p = urllib.parse.unquote(p)
            if os.path.isfile(p) and p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                if p not in self.image_paths:
                    self.image_paths.append(p)
                    added_count += 1

        if added_count > 0:
            self.log_msg(f"Đã thêm {added_count} ảnh vào Album.")
            self.render_album_slots()
            self.image_path_input.value = ""
        else:
            self.log_msg("Không có ảnh hợp lệ được thêm.",
                         color=COLORS["error"])

        self.page.update()

    def db_config_click(self, e):
        self.log_msg("Đã mở cấu hình DB (Đang sử dụng JSON mode).",
                     color=COLORS["accent"])

    def paste_image_from_clipboard(self, e):
        import os
        from PIL import ImageGrab
        from datetime import datetime

        try:
            # 1. Thử lấy ảnh gốc từ clipboard
            img = ImageGrab.grabclipboard()

            if img:
                if isinstance(img, list):
                    # Nếu là danh sách đường dẫn file (Mac Finder copy)
                    for path in img:
                        if os.path.exists(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                            self.image_paths.append(path)
                    self.log_msg(
                        f"✅ Đã dán {len(img)} đường dẫn ảnh từ clipboard.", color=COLORS["success"])
                else:
                    # Nếu là ảnh raw (pixel data) từ Snipping Tool / Chụp màn hình
                    temp_dir = "temp_images"
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir)

                    temp_path = os.path.abspath(os.path.join(
                        temp_dir, f"clipboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
                    img.save(temp_path, "PNG")
                    self.image_paths.append(temp_path)
                    self.log_msg(
                        "✅ Đã dán ảnh trực tiếp từ clipboard.", color=COLORS["success"])

                self.render_album_slots()
                return

            self.log_msg(
                "⚠️ Không tìm thấy ảnh hoặc đường dẫn hợp lệ trong clipboard.")
        except Exception as ex:
            self.log_msg(f"❌ Lỗi khi dán ảnh: {str(ex)}")

    def populate_groups(self):
        self.table_groups.rows.clear()

        # Đồng bộ trạng thái checkbox "Chọn tất cả" nếu trống
        if not self.groups_data:
            self.is_all_selected = False
            self.btn_select_all.bgcolor = COLORS["border"]
            self.btn_select_all.color = COLORS["text_main"]

        for idx, group in enumerate(self.groups_data):
            name = group.get("name", "")

            # Gán trạng thái selected cho group (mặc định False nếu chưa có)
            is_selected = group.get("selected", False)

            cb = ft.Checkbox(
                value=is_selected,
                on_change=self.create_toggle_group_handler(idx),
                fill_color={
                    ft.ControlState.HOVERED: COLORS["border"],
                    ft.ControlState.FOCUSED: COLORS["border"],
                    ft.ControlState.DEFAULT: COLORS["accent"] if is_selected else "transparent",
                    ft.ControlState.SELECTED: COLORS["accent"]
                },
                check_color=COLORS["text_main"]
            )

            # Gộp checkbox, name và nút xoá vào một DataCell duy nhất (vì chỉ có 1 cột)
            row_content = ft.Row([
                cb,
                ft.Text(name, color=COLORS["text_main"], size=13, tooltip=group.get(
                    "url", ""), expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=18,
                    icon_color=COLORS["error"],
                    tooltip="Delete",
                    on_click=self.create_delete_handler(idx)
                )
            ])

            self.table_groups.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(row_content),
                    ]
                )
            )
        self.page.update()

    def toggle_select_all_groups(self, e):
        self.is_all_selected = not self.is_all_selected

        # Cập nhật style nút ALL
        if self.is_all_selected:
            self.btn_select_all.bgcolor = COLORS["accent"]
            self.btn_select_all.color = "white"
        else:
            self.btn_select_all.bgcolor = COLORS["border"]
            self.btn_select_all.color = COLORS["text_main"]

        for group in self.groups_data:
            group["selected"] = self.is_all_selected
        self.populate_groups()

    def create_toggle_group_handler(self, idx):
        return lambda e: self.toggle_single_group(idx, e.control.value)

    def toggle_single_group(self, idx, is_checked):
        if 0 <= idx < len(self.groups_data):
            self.groups_data[idx]["selected"] = is_checked
            # Update 'select all' button state based on individual items
            all_selected = all(g.get("selected", False)
                               for g in self.groups_data)
            self.is_all_selected = all_selected

            if self.is_all_selected:
                self.btn_select_all.bgcolor = COLORS["accent"]
                self.btn_select_all.color = "white"
            else:
                self.btn_select_all.bgcolor = COLORS["border"]
                self.btn_select_all.color = COLORS["text_main"]

            self.page.update()

    def create_delete_handler(self, idx):
        return lambda e: self.delete_group(idx)

    def delete_group(self, idx):
        if 0 <= idx < len(self.groups_data):
            deleted = self.groups_data.pop(idx)
            save_groups(self.groups_data)
            self.log_msg(
                f"Group deleted: {deleted.get('name', '')}", color=COLORS["error"])
            self.populate_groups()

    def open_add_group_dialog(self, e):
        self.add_name_input.value = ""
        self.add_url_input.value = ""
        self.add_dialog.open = True
        self.page.update()

    open_add_dialog = open_add_group_dialog

    def close_add_dialog(self, e):
        self.add_dialog.open = False
        self.page.update()

    def confirm_add_group(self, e):
        try:
            name = self.add_name_input.value.strip()
            url = self.add_url_input.value.strip()

            # Vấn đề 4: Input Validation
            Validators.validate_group_name(name)
            Validators.validate_facebook_url(url)

            self.add_group_to_table(name, url)
            self.log_msg(f"✅ Nhóm '{name}' được thêm", color=COLORS["success"])
            self.close_add_dialog(None)

        except ValidationError as e:
            self.log_msg(f"❌ {str(e)}", color=COLORS["error"])
            self.show_snack(str(e), color=COLORS["error"])

    def add_group_to_table(self, name, url):
        self.groups_data.append({"name": name, "url": url, "selected": False})
        save_groups(self.groups_data)
        self.log_msg(f"Group added: {name}", color=COLORS["accent"])
        self.populate_groups()

    def open_settings_dialog(self, e):
        self.delay_min_input.value = str(self.post_delay_min)
        self.delay_max_input.value = str(self.post_delay_max)
        self.settings_dialog.open = True
        self.page.update()

    def close_settings_dialog(self, e):
        self.settings_dialog.open = False
        self.page.update()

    def confirm_settings(self, e):
        try:
            val_min = int(self.delay_min_input.value)
            val_max = int(self.delay_max_input.value)

            # Vấn đề 4: Validate delay range
            Validators.validate_delay_range(val_min, val_max)

            self.post_delay_min = val_min
            self.post_delay_max = val_max
            self.log_msg(
                f"✅ Delay được cập nhật: {val_min}s - {val_max}s", color=COLORS["success"])
            self.close_settings_dialog(e)
        except ValidationError as e:
            self.log_msg(f"❌ {str(e)}", color=COLORS["error"])
            self.show_snack(str(e), color=COLORS["error"])
        except ValueError:
            self.log_msg("❌ Delay phải là số nguyên", color=COLORS["error"])
            self.show_snack("Vui lòng nhập số", color=COLORS["error"])

    def get_selected_groups(self):
        """Get list of selected groups"""
        return [g for g in self.groups_data if g.get("selected")]

    def start_auto(self, e):
        import traceback
        import threading

        if self.is_running:
            self.show_snack("Auto is already running!",
                            color=COLORS["warning"])
            return

        selected_groups = self.get_selected_groups()
        if not selected_groups:
            self.show_snack("Please select at least one group!",
                            color=COLORS["error"])
            return

        self.is_running = True

        self.log_msg("✓ Auto started. Opening browser...",
                     color=COLORS["success"])
        self.show_snack(
            f"Starting auto post to {len(selected_groups)} groups...", color=COLORS["success"])

        # Run in background thread to prevent UI blocking
        thread = threading.Thread(
            target=self._run_auto_thread, args=(selected_groups,), daemon=True)
        thread.start()

    def _run_auto_thread(self, selected_groups):
        """Run auto in background thread"""
        import asyncio
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_facebook_auto(selected_groups))
        except Exception as ex:
            self.log_msg(
                f"❌ Auto error: {str(ex)[:100]}", color=COLORS["error"])
            self.is_running = False
        finally:
            loop.close()

    async def start_auto_clicked(self, e):
        # Hàm dự phòng cho code cũ
        self.start_auto(e)

    def stop_auto(self, e):
        self.is_running = False
        self.log_msg("Stopping auto...", color=COLORS["warning"])
        self.show_snack("Stopping auto. Please wait...")

    async def run_facebook_auto(self, selected_groups):
        import random
        # Bắt đầu vòng đời không phụ thuộc vào object nào (Keep Alive Browser)
        playwright_instance = getattr(self, "pw_instance", None)
        browser_context = getattr(self, "pw_context", None)

        # Theo dõi job
        job_id = len(self.history_list_view.controls) + 1
        current_time = datetime.now().strftime("%H:%M:%S")
        post_content = self.text_content.value.strip()
        thumb_img = self.image_paths[0] if self.image_paths else None
        target_group_names = [g.get("name", "Unknown")
                              for g in selected_groups]

        job_data = {
            "id": job_id,
            "time": current_time,
            "content": post_content if post_content else "(Chỉ đăng ảnh)",
            "thumbnail": thumb_img,
            "groups": target_group_names,
            "status": "Running"
        }
        self.add_to_history(job_data)
        final_status = "Success"

        # Hàm Helper "Siêu bền" xử lý Context Destroyed cho mọi action
        async def safe_action(action_func, log_prefix="Hành động"):
            for retry in range(3):
                if not self.is_running:
                    return False

                # Check if page is still valid before each retry
                try:
                    if page_pw.is_closed():
                        self.log_msg(f"{log_prefix}: Page đã đóng, không thể tiếp tục.",
                                     color=COLORS["error"], is_technical=True)
                        return False
                except Exception:
                    pass

                try:
                    await action_func()
                    self.log_msg(f"{log_prefix} thành công!",
                                 color=COLORS["success"], is_technical=True)
                    return True
                except Exception as e:
                    error_str = str(e)
                    # Check for context destroyed errors specifically
                    if "context" in error_str.lower() and "destroyed" in error_str.lower():
                        self.log_msg(
                            f"{log_prefix}: Lỗi context bị destroy: {error_str[:50]}...", color=COLORS["error"], is_technical=True)
                        return False
                    else:
                        self.log_msg(
                            f"Lỗi {log_prefix} (Thử lại {retry+1}/3): {error_str[:50]}...", color=COLORS["error"], is_technical=True)

                    if retry < 2:  # Don't sleep after last retry
                        await asyncio.sleep(2)
            return False

        try:
            self.log_msg("🚀 Bot đã sẵn sàng chiến đấu!",
                         color=COLORS["accent"], is_technical=True)

            if browser_context is None or playwright_instance is None:
                self.log_msg("Đang mở trình duyệt...",
                             color=COLORS["accent"], is_technical=True)
                playwright_instance = await async_playwright().start()
                self.pw_instance = playwright_instance

                user_data_dir = os.path.abspath(
                    os.path.join(os.getcwd(), "fb_user_data_edge"))
                if not os.path.exists(user_data_dir):
                    os.makedirs(user_data_dir)

                browser_context = await playwright_instance.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    channel="msedge",
                    args=['--disable-blink-features=AutomationControlled']
                )
                self.pw_context = browser_context

            # Get existing page or create a new one
            pages = browser_context.pages
            page_pw = pages[0] if pages else await browser_context.new_page()

            # Bơm ngụy trang tàng hình (Playwright Stealth) vào trình duyệt ngay lập tức
            try:
                stealth = Stealth()
                await stealth.apply_stealth_async(page_pw)
            except Exception as e:
                print(f"Stealth error: {e}")

            # Wait a bit before proceeding to Facebook
            await asyncio.sleep(2)

            # CƠ CHẾ CHỜ THÔNG MINH (SMART WAIT) TẠI TRANG CHỦ
            try:
                await page_pw.goto("https://www.facebook.com/")
            except Exception as e:
                self.log_msg(
                    f"Lỗi khi truy cập Facebook: {str(e)[:50]}", color=COLORS["error"], is_technical=True)
                if not self.is_running:
                    return

            try:
                await page_pw.wait_for_selector('div[role="main"]', timeout=30000)
            except Exception as e:
                self.log_msg(
                    f"⚠️ Timeout waiting for main div: {str(e)[:50]}", is_technical=True)

            # Đăng ký bắt event dialog để tự động Accept cảnh báo rời trang
            try:
                page_pw.on(
                    "dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            except Exception as e:
                self.log_msg(
                    f"Lỗi đăng ký dialog handler: {str(e)[:50]}", is_technical=True)

            # Cho phép người dùng đăng nhập bằng tay nếu chưa
            is_login_page = False
            try:
                # Kiểm tra URL trước, sau đó kiểm tra element (an toàn hơn)
                is_login_page = "login" in page_pw.url
                if not is_login_page:
                    try:
                        is_login_page = bool(await page_pw.query_selector("input[name='email']"))
                    except Exception:
                        # Context destroyed, assume not login page
                        is_login_page = "login" in page_pw.url
            except Exception:
                is_login_page = "login" in page_pw.url

            if is_login_page:
                self.log_msg("Đang chờ người dùng đăng nhập tay... Bạn có 120 giây.",
                             color=COLORS["error"], is_technical=True)
                for _ in range(120):
                    if not self.is_running:
                        return
                    try:
                        still_login = "login" in page_pw.url
                        if not still_login:
                            try:
                                # Safely check for login element
                                login_elem = await page_pw.query_selector("input[name='email']")
                                still_login = bool(login_elem)
                            except Exception:
                                # Context destroyed, assume logged in
                                still_login = False

                        if not still_login:
                            break
                    except Exception:
                        # Context destroyed or page error, assume logged in
                        break
                    await asyncio.sleep(1)

                try:
                    await page_pw.wait_for_selector('div[role="main"]', timeout=60000)
                    timestamp = datetime.now().strftime("%H:%M")
                    self.log_msg(f"[{timestamp}] Đã nhận diện được trang chủ Facebook.",
                                 color=COLORS["success"], is_technical=True)
                except Exception as e:
                    self.log_msg(
                        f"Lỗi xác nhận sau khi đăng nhập (có thể context bị destroy): {str(e)[:50]}", color=COLORS["error"], is_technical=True)

            # Ổn định sau khi đăng nhập/lấy Newsfeed
            timestamp = datetime.now().strftime("%H:%M")
            self.log_msg(f"[{timestamp}] Đang ổn định hệ thống. Nghỉ 5s trước khi tương tác...",
                         color=COLORS["text_muted"], is_technical=True)
            await asyncio.sleep(5)

            # Bắt đầu duyệt từng nhóm
            for i, group in enumerate(selected_groups, start=1):
                if not self.is_running:
                    self.log_msg("ĐÃ DỪNG AUTO BỞI NGƯỜI DÙNG.")
                    final_status = "Failed"
                    break

                group_url = group.get("url")
                group_name = group.get("name")
                timestamp = datetime.now().strftime("%H:%M")
                self.log_msg(
                    f"[{timestamp}] #{i}/{len(selected_groups)} - Đang di chuyển tới Group: {group_name}...", is_technical=True)

                # 📝 Load content RIGHT AWAY at the start of each group (CRITICAL FIX)
                content = self.text_content.value.strip()
                self.log_msg(
                    f"📊 Images available: {len(self.image_paths)} | Content: {len(content)} chars", color=COLORS["text_muted"], is_technical=True)

                try:
                    try:
                        await page_pw.goto(group_url, wait_until="domcontentloaded", timeout=60000)
                        self.log_msg(
                            f"✓ Đã load URL nhóm thành công", is_technical=True)
                    except Exception as e:
                        self.log_msg(
                            f"⚠️ Lỗi goto (context may be destroyed): {str(e)[:50]}", is_technical=True)
                        # Retry or continue
                        await asyncio.sleep(2)

                    try:
                        await page_pw.wait_for_selector('div[role="main"]', timeout=30000)
                        self.log_msg(f"✓ Trang chính đã load",
                                     is_technical=True)
                    except Exception as e:
                        self.log_msg(
                            f"⚠️ Wait timeout main div: {str(e)[:50]}", is_technical=True)
                        pass

                    # 🔄 Extra wait to ensure page is fully interactive
                    self.log_msg(f"⏳ Ổn định trang (chờ 4s)...",
                                 color=COLORS["text_muted"], is_technical=True)
                    await asyncio.sleep(4)

                    # 🔍 Check page state before proceeding
                    try:
                        page_title = await page_pw.title()
                        self.log_msg(
                            f"📄 Page title: {page_title[:40]}...", is_technical=True)
                    except Exception:
                        pass

                    # 🔄 For Group 2+: Ensure page is fully refreshed (clear any stale elements)
                    if i > 1:
                        self.log_msg(
                            f"🔄 Refresh page state for Group {i}...", color=COLORS["text_muted"], is_technical=True)
                        try:
                            # Scroll to top to reset page
                            await page_pw.keyboard.press("Home")
                            await asyncio.sleep(1)
                        except Exception:
                            pass

                    if not self.is_running:
                        break

                    # 1. Tìm ô "Bạn đang nghĩ gì?" - Sử dụng Dynamic Selector
                    async def click_box():
                        log_info(
                            f"Tìm post input box trong nhóm: {group_name}")

                        # Khởi tạo dynamic selector
                        selector = DynamicSelector(page_pw)

                        # Tìm element
                        post_input = await selector.find_post_input_box()

                        if post_input is None:
                            log_error(
                                f"Không tìm thấy post input box trong nhóm {group_name}")
                            raise Exception("Post input box không tìm thấy")

                        # Click vào
                        await post_input.click()
                        log_info(f"✓ Đã click post input box thành công")

                    box_clicked = await safe_action(click_box, log_prefix="Click ô nhập bài")

                    if not box_clicked:
                        self.log_msg(
                            f"⚠️ Nhóm này khó nhằn quá, tôi sẽ thử lại ở nhóm sau! (Không thấy ô đăng bài)", color=COLORS["error"])
                        continue

                    await asyncio.sleep(3)
                    if not self.is_running:
                        break

                    # 2. Gõ nội dung văn bản (Gõ mù ngay vị trí con trỏ chuột)
                    if content:
                        async def fill_text():
                            try:
                                self.log_msg(
                                    "Bắt đầu gõ nội dung (mù)...", is_technical=True)
                                # FB tự động focus vào ô nhập liệu, ra lệnh gõ trực tiếp luôn
                                for char in content:
                                    # 1. Giả lập gõ sai và sửa lỗi (Tỷ lệ 5% với chữ cái)
                                    if random.random() < 0.05 and char.isalpha():
                                        wrong_char = random.choice(
                                            'abcdefghijklmnopqrstuvwxyz')
                                        try:
                                            await page_pw.keyboard.type(wrong_char)
                                        except Exception:
                                            # Context may be destroyed
                                            raise Exception(
                                                "Context destroyed during typing")
                                        # Khựng lại nhận ra lỗi
                                        await asyncio.sleep(random.uniform(0.1, 0.4))
                                        try:
                                            # Xóa chữ sai
                                            await page_pw.keyboard.press("Backspace")
                                        except Exception:
                                            raise Exception(
                                                "Context destroyed during typing")
                                        # Nghỉ nhịp trước khi gõ chữ đúng
                                        await asyncio.sleep(random.uniform(0.1, 0.3))

                                    # 2. Gõ chữ đúng
                                    try:
                                        await page_pw.keyboard.type(char)
                                    except Exception:
                                        raise Exception(
                                            "Context destroyed during typing")
                                    # Tốc độ gõ mổ cò bình thường
                                    await asyncio.sleep(random.uniform(0.03, 0.15))

                                    # 3. Giả lập dừng lại suy nghĩ (Tỷ lệ 3%)
                                    if random.random() < 0.03:
                                        # Dừng 1-3 giây giữa chừng
                                        await asyncio.sleep(random.uniform(1.0, 3.0))
                            except Exception as e:
                                if "context" in str(e).lower():
                                    raise Exception(
                                        "Context destroyed during typing")
                                raise

                        await safe_action(fill_text, log_prefix="Điền nội dung")
                        await asyncio.sleep(2)

                    if not self.is_running:
                        break

                    # 3. Đăng ảnh nếu có - Sử dụng Dynamic Selector
                    if self.image_paths:
                        async def upload_imgs():
                            log_info(
                                f"Bắt đầu upload {len(self.image_paths)} ảnh")
                            abs_image_paths = [os.path.abspath(
                                p) for p in self.image_paths]

                            self.log_msg(
                                "Đang lướt tìm ảnh...", color=COLORS["text_muted"], is_technical=True)
                            await asyncio.sleep(random.uniform(3.0, 6.0))

                            # Sử dụng dynamic selector tìm file input
                            selector = DynamicSelector(page_pw)
                            input_file = await selector.find_file_input()

                            # Log chi tiết file input search
                            if input_file is None:
                                log_error(
                                    f"❌ LỖI: Không tìm thấy file input element trong nhóm {group_name}")
                                self.log_msg(
                                    f"⚠️ Chi tiết: Đã tìm file input nhưng không thấy", color=COLORS["error"], is_technical=True)
                                raise Exception("File input không tìm thấy")

                            # Log trước khi upload
                            self.log_msg(
                                f"📸 Uploading {len(abs_image_paths)} ảnh vào Facebook...", color=COLORS["accent"], is_technical=True)

                            await input_file.set_input_files(abs_image_paths)
                            log_info(
                                f"✓ Đã upload {len(abs_image_paths)} ảnh thành công")
                            self.log_msg(
                                f"✅ Upload image thành công: {len(abs_image_paths)} ảnh", color=COLORS["success"], is_technical=True)

                            self.log_msg(
                                "Đợi Facebook xử lý ảnh...", color=COLORS["text_muted"], is_technical=True)
                            await asyncio.sleep(random.uniform(2.0, 4.0))

                        success = await safe_action(upload_imgs, log_prefix="Mở và đính kèm Upload")
                        if success:
                            timestamp_img = datetime.now().strftime("%H:%M")
                            self.log_msg(
                                f"[{timestamp_img}] Đang chờ ảnh tải lên hệ thống...", is_technical=True)
                            await asyncio.sleep(5)
                        else:
                            # ❌ Upload ảnh THẤT BẠI - Skip group này để tránh post chỉ có text
                            self.log_msg(
                                f"❌ Nhóm {group_name}: Lỗi upload ảnh - bỏ qua nhóm này", color=COLORS["error"])
                            continue

                    if not self.is_running:
                        break
                    await asyncio.sleep(3)

                    # 3.5 QUALITY CONTROL: Kiểm tra nội dung trước khi đăng (phải có text HOẶC ảnh)
                    has_content = bool(content.strip()) if content else False
                    has_images = len(self.image_paths) > 0

                    if not has_content and not has_images:
                        self.log_msg(
                            f"⚠️ Nhóm {group_name}: Bỏ qua - không có nội dung và không có ảnh!", color=COLORS["error"])
                        continue
                    elif not has_content:
                        self.log_msg(
                            f"⚠️ Nhóm {group_name}: Chỉ đăng {len(self.image_paths)} ảnh (không có text)", color=COLORS["accent"])
                    elif not has_images:
                        self.log_msg(
                            f"⚠️ Nhóm {group_name}: Chỉ đăng text (không có ảnh)", color=COLORS["accent"])
                    else:
                        self.log_msg(
                            f"✓ Nhóm {group_name}: Sẽ đăng text ({len(content)} ký tự) + {len(self.image_paths)} ảnh", color=COLORS["accent"])

                    # 4. Bấm chữ Đăng (Post) - Sử dụng Dynamic Selector
                    async def click_post():
                        try:
                            log_info(
                                f"Tìm và click post button trong nhóm {group_name}")

                            # Thử phím tắt trước
                            self.log_msg(
                                "Đang thử đăng bài bằng phím tắt (Control+Enter)...", is_technical=True)
                            try:
                                await page_pw.keyboard.press("Control+Enter")
                            except Exception:
                                self.log_msg(
                                    "Phím tắt không work, sẽ thử click nút", is_technical=True)
                            await asyncio.sleep(2)

                            # Sử dụng dynamic selector tìm nút Đăng
                            selector = DynamicSelector(page_pw)
                            post_button = await selector.find_post_button()

                            if post_button is not None:
                                self.log_msg(
                                    "Thử click nút Đăng...", is_technical=True)
                                try:
                                    await post_button.click(timeout=5000)
                                except Exception as e:
                                    if "context" in str(e).lower():
                                        raise Exception(
                                            "Context destroyed during post click")
                                    raise
                                log_info("✓ Đã click post button thành công")
                            else:
                                log_warning(
                                    "Không tìm thấy post button, có thể phím tắt đã work")
                        except Exception as e:
                            if "context" in str(e).lower():
                                raise
                            raise

                    submit_clicked = await safe_action(click_post, log_prefix="Click Đăng Bài")

                    # Cơ chế Screenshot Fallback nếu không Đăng được
                    if not submit_clicked:
                        self.log_msg("❌ Không thể click nút Đăng. Cần kiểm tra lại giao diện Facebook.",
                                     color=COLORS["error"], is_technical=True)
                        self.log_msg(
                            f"⚠️ Nhóm này khó nhằn quá, tôi sẽ thử lại ở nhóm sau!", color=COLORS["error"])
                        err_dir = "error_screenshots"
                        if not os.path.exists(err_dir):
                            os.makedirs(err_dir)
                        try:
                            await page_pw.screenshot(path=os.path.join(err_dir, f"error_{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
                        except Exception as screenshot_err:
                            self.log_msg(
                                f"Không thể chụp screenshot: {str(screenshot_err)[:50]}", is_technical=True)
                        continue

                    # ✅ Đăng bài THÀNH CÔNG
                    self.log_msg("✅ Đã đăng bài thành công!",
                                 is_technical=True)

                    # Chờ cho đến khi popup đăng bài biến mất
                    await asyncio.sleep(8)
                    self.log_msg(
                        f"Hoàn thành nhóm {i}/{len(selected_groups)}.", color=COLORS["success"])

                    # 5. Clean up: Nhấn Escape 2 lần để tắt popup/dialog còn sót
                    try:
                        await page_pw.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                        await page_pw.keyboard.press("Escape")
                        await asyncio.sleep(1)
                    except Exception as e:
                        self.log_msg(
                            f"Cleanup lỗi (context có thể bị destroy): {str(e)[:50]}", is_technical=True)

                except Exception as group_err:
                    error_str = str(group_err)
                    if "context" in error_str.lower() and "destroyed" in error_str.lower():
                        self.log_msg(
                            f"⚠️ Nhóm {group_name}: Context bị destroy (có thể do navigation)", color=COLORS["error"])
                    else:
                        self.log_msg(
                            f"⚠️ Lỗi xử lý nhóm {group_name}: {error_str[:50]}...", color=COLORS["error"])
                    # Không set final_status = "Failed" ở đây để không kết thúc hoàn toàn
                    # Chỉ ghi log và sang nhóm tiếp theo.

                # Nghỉ giữa mỗi nhóm nếu không phải nhóm cuối cùng
                if i < len(selected_groups):
                    delay = random.randint(
                        self.post_delay_min, self.post_delay_max)
                    # Chỉ hiển thị 1 message, không cập nhật liên tục
                    self.log_msg(
                        f"⏳ Chờ {delay}s trước nhóm tiếp theo", color=COLORS["text_muted"])
                    await asyncio.sleep(delay)

            # ✅ TẤT CẢ NHÓM HOÀN THÀNH - Dọn dẹp dữ liệu (Clear images NGOÀI vòng lặp)
            self.log_msg(
                "✓ Hoàn thành tất cả nhóm! Đang dọn dẹp dữ liệu...", is_technical=True)
            self.clear_all_images()  # BẮT BUỘC: Clear images SAU KHI tất cả nhóm đều post xong

        except Exception as e:
            self.log_msg(f"Lỗi hệ thống: {str(e)}",
                         color=COLORS["error"], is_technical=True)
            final_status = "Failed"

        finally:
            # Vấn đề 3: Clean up browser context properly
            try:
                if browser_context:
                    await browser_context.close()
                    self.log_msg("✓ Browser context closed", is_technical=True)
                if playwright_instance:
                    await playwright_instance.stop()
                    self.log_msg("✓ Playwright stopped", is_technical=True)
            except Exception as cleanup_error:
                self.log_msg(
                    f"Browser cleanup failed: {str(cleanup_error)}", is_technical=True)

            # Reset instance variables
            self.pw_context = None
            self.pw_instance = None

            self.is_running = False

            # Cập nhật lịch sử
            if len(self.history_list_view.controls) > 0:
                self.history_list_view.controls.pop(0)
                job_data["status"] = final_status
                self.add_to_history(job_data)

            self.log_msg("Đã dừng tất cả hoạt động.",
                         color=COLORS["text_muted"], is_technical=True)
            await asyncio.sleep(2)
            self.page.update()
