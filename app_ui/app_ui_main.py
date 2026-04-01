from exceptions import TooManyPostsException, ContextDestroyedException
from detection_limiter import DetectionLimiter
from validators import Validators, ValidationError
from ui_messages import get_message, get_message_color
from dynamic_selector import DynamicSelector
from logger_config import log_debug, log_info, log_warning, log_error, log_exception
from recovery_manager import recovery_manager
from retry_logic import retry_async
from posting_engine import PostingEngine
from playwright.async_api import async_playwright
from storage import load_groups, save_groups
from app_ui.ui_history import HistoryManager
from app_ui.ui_logging import LogManager
from app_ui.update_manager import UpdateManager, APP_VERSION
from app_ui.settings_manager import SettingsManager
import urllib.parse
import flet as ft
import os
import sys
import asyncio
import threading
import time
import json
from datetime import datetime
from PIL import ImageGrab
import yaml

# Import Playwright Stealth (chính xác)
from playwright_stealth import Stealth

import nest_asyncio
nest_asyncio.apply()

from thread_safety import get_auto_runner, get_modification_guard
auto_runner = get_auto_runner()
mod_guard = get_modification_guard()

# Get base path for bundled resources (PyInstaller or development)


from utils import get_resource_path, get_writable_path, restart_application

# Load configuration from config.yaml


def load_config(config_file="config.yaml"):
    """Load configuration from YAML file.
    
    Priority: 1) User writable copy next to exe, 2) Bundled resource in _MEIPASS
    """
    try:
        # Try user writable copy first (next to exe)
        writable_path = get_writable_path(config_file)
        if os.path.exists(writable_path):
            with open(writable_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        # Fall back to bundled resource (read-only, in _MEIPASS)
        config_path = get_resource_path(config_file)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        log_error(f"Error loading config: {e}")

    # Return default config if file not found
    return {
        "window": {"width": 1400, "height": 850},
        "delays": {"post_min": 5, "post_max": 10},
        "detection": {"max_posts_per_session": 10, "max_posts_per_day": 25}
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

# App Version
VERSION = APP_VERSION

# Get values from config
FONT_FAMILY = CONFIG.get("ui", {}).get(
    "font_family", "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif")
HISTORY_FILE = get_writable_path(CONFIG.get("logging", {}).get("history_file", "history.json"))
MAX_HISTORY_ITEMS = CONFIG.get("logging", {}).get("max_history_items", 100)


class AppUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config = CONFIG  # Store config for helper classes
        self.colors = COLORS  # Store colors for helper classes
        self.groups_data = load_groups()
        self.image_paths = []  # Danh sách ảnh chờ đăng
        # self.is_running is now managed by thread_safety module

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
        self.update_manager = UpdateManager()
        self.settings_manager = SettingsManager()
        self.settings_manager.app_ui = self  # Pass reference for callbacks

        # Update UI elements (will be set in build_ui)
        self.version_text = None
        self.update_button = None
        self.updating = False

        self.posting_progress_container = None
        self.update_progress_container = None
        self.update_progress_text = None
        self.update_progress_bar = None
        self.posting_progress_text = None
        self.posting_progress_bar = None

        self.setup_page()
        self.build_ui()
        self.populate_groups()

        # Check for updates in background
        self.check_for_updates_async()

        # Show "Bot ready" message after initialization
        self.log_msg(get_message("bot_ready"), color=COLORS["accent"])

        # Check for recovery state from previous crash
        self._check_recovery_on_startup()

    def setup_page(self):
        """Cấu hình cửa sổ Flet App"""
        self.page.title = "Auto Posting"
        # Set window icon with correct path for both development and PyInstaller bundle
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.page.window.icon = icon_path
            log_debug(f"Window icon loaded: {icon_path}")
        else:
            log_warning(f"Icon file not found at: {icon_path}")
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

        # Set minimum window size to prevent UI overflow when resizing
        # These values ensure all UI elements remain visible and usable
        self.page.window.min_width = 1200
        self.page.window.min_height = 700

        log_info(f"Window size: {self.page.window.width}x{self.page.window.height}, "
                 f"Min size: {self.page.window.min_width}x{self.page.window.min_height}")

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

    def make_card(self, title, content, expand=False, padding=15, center_title=False):
        """Hàm dựng các hộp nội dung (Cards) nhất quán"""
        # Internal title padding if container padding is set to 0
        title_padding = ft.padding.only(left=20, top=15, right=20) if padding == 0 else 0
        
        container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(title, weight="bold", size=16,
                            color=COLORS["text_main"]),
                    padding=title_padding,
                    alignment=ft.Alignment(0, 0) if center_title else ft.Alignment(-1, 0)
                ),
                ft.Divider(color=COLORS["border"], height=1),
                content
            ], spacing=0 if padding == 0 else 15, expand=expand),
            padding=padding,
            bgcolor=COLORS["bg_card"],
            border_radius=15, # Softer corners
            border=ft.Border.all(
                1, COLORS["border"]) if COLORS["border"] else None,
            expand=expand,
            margin=ft.margin.only(bottom=15),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color="#4D000000", # Black with ~30% opacity
                offset=ft.Offset(0, 4),
            )
        )
        return container

    def build_ui(self):
        """Xây dựng và Lắp ráp Giao diện UI: LAYOUT 3 CỘT FACEBOOK NIGHT MODE"""

        # --- HEADER (Thanh điều hướng trên cùng giả lập Facebook) ---
        header_container = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.FACEBOOK, color=COLORS["accent"], size=40),
                    ft.Text("Auto Posting by Tristan", size=24,
                            weight="w800", color=COLORS["text_main"])
                ], spacing=10),
                ft.Container(expand=True),  # Khoảng trống giữa
            ], alignment="spaceBetween", vertical_alignment="center"),
            padding=ft.padding.only(left=20, right=20, top=10, bottom=10),
            border=ft.Border(bottom=ft.BorderSide(1, COLORS["border"])),
            bgcolor=COLORS["bg_card"]
        )

        header_items = [header_container]

        # Add dry run warning banner if enabled
        if CONFIG.get("app", {}).get("dry_run", False):
            header_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING, color="white", size=20),
                        ft.Text("🧪 DRY RUN MODE - Sẽ không đăng bài thực tế",
                                color="white", size=14, weight="bold")
                    ], spacing=10, vertical_alignment="center", alignment="center"),
                    bgcolor="#FF9800",
                    padding=8,
                    width=float("inf") # Full width
                )
            )
        
        header = ft.Column(header_items, spacing=0)

        # ================= CỘT TRÁI (MENU & CÔNG CỤ) - Chiếm khoảng 20% =================
        # --- PROGRESS UI DEFINITIONS ---
        # 1. Posting Progress Bar
        self.posting_progress_text = ft.Text(
            "", size=11, color=COLORS["text_muted"], weight="w500")
        self.posting_progress_bar = ft.ProgressBar(
            value=0, color=COLORS["accent"], bgcolor=COLORS["border"], height=4)
        self.posting_progress_container = ft.Container(
            content=ft.Column([
                self.posting_progress_text,
                self.posting_progress_bar
            ], spacing=5),
            margin=ft.margin.only(bottom=10, left=10, right=10),
            visible=False
        )

        # 2. Update Progress Bar
        self.update_progress_text = ft.Text(
            "", size=11, color=COLORS["text_muted"], weight="w500")
        self.update_progress_bar = ft.ProgressBar(
            value=0, color=COLORS["success"], bgcolor=COLORS["border"], height=4)
        self.update_progress_container = ft.Container(
            content=ft.Column([
                self.update_progress_text,
                self.update_progress_bar
            ], spacing=5),
            margin=ft.margin.only(bottom=10, left=10, right=10),
            visible=False
        )

        # Update button ref so we can hide it later
        self.btn_check_update_menu = self.make_menu_item(
            ft.Icons.SYSTEM_UPDATE, "Check Update", COLORS["accent"], self.manual_check_updates)

        menu_items = ft.Column([
            self.make_menu_item(ft.Icons.ROCKET_LAUNCH,
                                "Start Auto", COLORS["accent"], self.start_auto),
            self.posting_progress_container,
            self.make_menu_item(ft.Icons.STOP_CIRCLE, "Stop",
                                COLORS["error"], self.stop_auto),
            ft.Divider(color=COLORS["border"]),
            self.make_menu_item(ft.Icons.GROUP_ADD, "Add Group",
                                COLORS["success"], self.open_add_group_dialog),
            self.make_menu_item(ft.Icons.HISTORY, "History",
                                COLORS["text_main"], self.toggle_history_view),
            self.make_menu_item(ft.Icons.SETTINGS, "Settings",
                                COLORS["text_main"], self.toggle_settings_view),
            self.btn_check_update_menu,
            self.update_progress_container,
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

        # Version and Update display (in History tab)
        self.version_text = ft.Text(
            f"v{VERSION}",
            size=12,
            color=COLORS["text_muted"],
            weight="w500"
        )

        self.update_button = ft.IconButton(
            ft.Icons.SYSTEM_UPDATE,
            icon_size=16,
            icon_color=COLORS["accent"],
            tooltip="Check for updates",
            on_click=self.manual_check_updates,
            visible=True
        )

        self.update_status_text = ft.Text(
            "",
            size=11,
            color=COLORS["text_muted"]
        )

        history_header = ft.Row([
            ft.Text("Post History", size=20, weight="bold",
                    color=COLORS["text_main"]),
            ft.Container(expand=True),  # Spacer
            btn_back_home
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment="center")

        self.post_history_col = ft.Column([
            history_header,
            ft.Divider(color=COLORS["border"]),
            self.history_list_view
        ], expand=True, visible=False)

        # ================= SETTINGS TAB =================
        btn_back_settings = ft.IconButton(
            ft.Icons.ARROW_BACK,
            icon_color=COLORS["text_main"],
            on_click=self.toggle_settings_view
        )

        settings_header = ft.Row([
            ft.Text("Settings", size=20, weight="bold",
                    color=COLORS["text_main"]),
            ft.Container(expand=True),  # Spacer
            btn_back_settings
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment="center")

        settings_content = self.settings_manager.build_settings_ui(COLORS)

        self.settings_col = ft.Column([
            settings_header,
            ft.Divider(color=COLORS["border"]),
            settings_content
        ], expand=True, visible=False)

        col_center = ft.Container(
            content=ft.Stack([
                self.post_compose_col,
                self.post_history_col,
                self.settings_col
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

        # Pre-allocate Update Dialog (Problem Fix #10: Consistent initialization at startup)
        self.update_dialog = ft.AlertDialog(
            title=ft.Text("Mới nhất", color=COLORS["text_main"]),
            bgcolor=COLORS["bg_card"],
            content=ft.Text("Đang tải dữ liệu...", size=13, color=COLORS["text_muted"]),
            actions=[]
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
                ft.Text("Logs View:", size=12, weight="bold",
                        color=COLORS["text_muted"]),
                ft.Row([
                    btn_user_messages,
                    ft.VerticalDivider(color=COLORS["border"], width=1),
                    btn_technical_logs,
                ], spacing=10, alignment="center"),
                ft.Container(expand=True),  # Spacer
                ft.IconButton(
                    ft.Icons.FILE_DOWNLOAD_OUTLINED,
                    tooltip="Export as .txt",
                    on_click=self.export_logs,
                    icon_color=COLORS["text_muted"],
                    icon_size=18
                )
            ], alignment="center", vertical_alignment="center", spacing=20),
            padding=ft.padding.symmetric(horizontal=15, vertical=5),
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
            expand=True,
            center_title=True
        )

        col_right = ft.Container(
            content=ft.Column([card_groups, card_logs], expand=True),
            padding=ft.padding.only(top=20, left=10, right=20, bottom=20),
            expand=3
        )

        # ================= VERSION & UPDATE FOOTER (Bottom-Left) =================
        self.version_text = ft.Text(
            f"v{VERSION}",
            size=12,
            color=COLORS["text_muted"],
            weight="w500"
        )

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
        self.page.overlay.append(self.update_dialog)

        # Fix #9: Load history from persistent file on startup
        self.history_manager.load_from_file()

        self.page.update()

    def make_menu_item(self, icon, text, color, on_click):
        """Tạo nút menu bên trái phong cách Facebook hiện đại"""
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=24),
                ft.Text(text, size=15, weight="w500",
                        color=COLORS["text_main"])
            ], spacing=15),
            padding=ft.padding.symmetric(horizontal=15, vertical=12),
            border_radius=10,
            on_click=on_click,
            ink=True,
            on_hover=self.on_menu_hover,
            animate=ft.Animation(300, "decelerate")
        )

    def on_menu_hover(self, e):
        # 10% opacity blue accent
        e.control.bgcolor = "#1A1877F2" if e.data == "true" else "transparent"
        e.control.update()

    def toggle_history_view(self, e):
        """Chuyển đổi qua lại giữa màn hình Soạn bài và Lịch sử"""
        is_history_visible = not self.post_history_col.visible
        self.post_history_col.visible = is_history_visible
        self.post_compose_col.visible = not is_history_visible
        self.settings_col.visible = False
        self.page.update()

    def toggle_settings_view(self, e):
        """Chuyển đổi qua lại giữa màn hình Soạn bài và SettingsSettings"""
        is_settings_visible = not self.settings_col.visible
        self.settings_col.visible = is_settings_visible
        self.post_compose_col.visible = not is_settings_visible
        self.post_history_col.visible = False
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

    def show_snack(self, message, color=COLORS["bg_card"]):
        """Hiển thị thông báo (SnackBar) góc dưới màn hình"""
        # Always use white text for better visibility on any background
        self.page.overlay.append(
            ft.SnackBar(
                ft.Text(message, color="white", size=14, weight="w500"),
                bgcolor=color,
                duration=3000,
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
        export_filename = get_writable_path(f"logs/vibecode_export_{timestamp}.txt")

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
                except Exception as e:
                    # Fallback if image fails to load
                    log_debug(f"Failed to load image thumbnail: {str(e)}")
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
        import threading

        if auto_runner.is_running():
            self.show_snack("Auto is đã đang chạy!",
                            color=COLORS["warning"])
            return

        if self.updating:
            self.show_snack("⚠️ Đang trong quá trình cập nhật! Vui lòng chờ.",
                            color=COLORS["warning"])
            self.log_msg("❌ Không thể chạy Auto trong khi đang tải cập nhật.",
                         color=COLORS["warning"])
            return

        selected_groups = self.get_selected_groups()
        if not selected_groups:
            self.show_snack("Please select at least one group!",
                            color=COLORS["error"])
            return

        # Validate: must have at least text or images
        post_content = self.text_content.value.strip() if self.text_content.value else ""
        has_content = bool(post_content)
        has_images = len(self.image_paths) > 0

        if not has_content and not has_images:
            self.show_snack("Vui lòng nhập nội dung hoặc thêm ảnh!",
                            color=COLORS["error"])
            self.log_msg("❌ Không có nội dung và không có ảnh. Vui lòng nhập nội dung hoặc thêm ảnh trước khi đăng.",
                         color=COLORS["error"])
            return

        # Use runner and guard
        auto_runner.can_start()  # Mark as running
        mod_guard.set_automation_running(True)

        self.log_msg("✓ Auto started. Opening browser...",
                     color=COLORS["success"])
        self.show_snack(
            f"Starting auto post to {len(selected_groups)} groups...", color=COLORS["success"])

        # Run in background thread to prevent UI blocking
        thread = threading.Thread(
            target=self._run_auto_thread, args=(selected_groups,), daemon=True)
        thread.start()

    def _run_auto_thread(self, selected_groups):
        """Run auto in background thread using PostingEngine"""
        import asyncio
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            engine = PostingEngine(self)
            loop.run_until_complete(engine.run_facebook_auto(selected_groups))
        except Exception as ex:
            self.log_msg(
                f"❌ Auto error: {str(ex)[:100]}", color=COLORS["error"])
            auto_runner.mark_finished()
            mod_guard.set_automation_running(False)
        finally:
            self.update_posting_progress(0, 0, "", finished=True)
            loop.close()

    def stop_auto(self, e):
        auto_runner.stop()
        mod_guard.set_automation_running(False)
        self.log_msg("Stopping auto...", color=COLORS["warning"])
        self.show_snack("Stopping auto. Please wait...",
                        color=COLORS["warning"])
        self.posting_progress_text.value = "Đang dừng..."
        self.posting_progress_bar.color = COLORS["error"]
        self.page.update()

    def update_posting_progress(self, current_index: int, total: int, current_group_name: str, finished: bool = False):
        """Update the posting progress UI in the sidebar"""
        if finished:
            self.posting_progress_text.value = "✅ Hoàn thành 100%"
            self.posting_progress_bar.value = 1.0
            self.posting_progress_bar.color = COLORS["success"]
            # After 3 seconds, hide it
            threading.Timer(3.0, self._hide_posting_progress).start()
        else:
            self.posting_progress_container.visible = True
            self.posting_progress_bar.color = COLORS["accent"]
            # Calculate value
            progress_value = current_index / total if total > 0 else 0
            self.posting_progress_bar.value = progress_value
            # Trim group name if too long
            short_group = current_group_name[:15] + "..." if len(current_group_name) > 15 else current_group_name
            self.posting_progress_text.value = f"Đang đăng: {current_index}/{total} ({short_group})"
            
        self.page.update()

    def _hide_posting_progress(self):
        self.posting_progress_container.visible = False
        self.page.update()

    # NOTE: run_facebook_auto() has been moved to posting_engine.py (PostingEngine class)
    # This keeps AppUI focused on UI concerns while PostingEngine handles automation.

    # === RECOVERY RESUME FEATURE ===

    def _check_recovery_on_startup(self):
        """Check for recovery state on app startup and show resume dialog if found"""
        try:
            if not recovery_manager.has_recovery_state():
                return

            summary = recovery_manager.get_summary()
            if not summary or summary["remaining"] == 0:
                # No valid remaining groups, clear stale state
                recovery_manager.clear_recovery_state()
                return

            # Format timestamp for display
            try:
                from datetime import datetime as dt
                ts = dt.fromisoformat(summary["timestamp"])
                time_str = ts.strftime("%d/%m/%Y %H:%M:%S")
            except Exception:
                time_str = summary["timestamp"]

            # Build info text
            info_parts = []
            info_parts.append(f"⏰ Thời gian crash: {time_str}")
            info_parts.append(f"📊 Đã đăng: {summary['posted']}/{summary['total']} nhóm")
            info_parts.append(f"📋 Còn lại: {summary['remaining']} nhóm chưa đăng")
            if summary["has_content"]:
                info_parts.append(f"📝 Có nội dung text")
            if summary["has_images"]:
                info_parts.append(f"🖼️ Có {summary['image_count']} ảnh")
            if summary["failed_groups"]:
                info_parts.append(f"❌ Nhóm lỗi: {', '.join(summary['failed_groups'][:3])}")

            info_text = "\n".join(info_parts)

            # Show recovery dialog
            self._recovery_dialog = ft.AlertDialog(
                title=ft.Text("⚠️ Phát hiện phiên đăng bài bị gián đoạn",
                              color=COLORS["warning"], weight="bold", size=16),
                bgcolor=COLORS["bg_card"],
                content=ft.Column([
                    ft.Container(
                        content=ft.Text(
                            info_text,
                            color=COLORS["text_main"],
                            size=13,
                        ),
                        padding=15,
                        bgcolor=COLORS["bg_main"],
                        border_radius=8,
                        border=ft.border.all(1, COLORS["border"])
                    ),
                    ft.Text(
                        "Bạn có muốn tiếp tục đăng bài từ chỗ bị gián đoạn?",
                        color=COLORS["text_muted"],
                        size=12,
                        italic=True
                    )
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton(
                        "Bỏ qua",
                        style=ft.ButtonStyle(color=COLORS["text_muted"]),
                        on_click=self._dismiss_recovery
                    ),
                    ft.ElevatedButton(
                        "Tiếp tục đăng",
                        icon=ft.Icons.PLAY_ARROW,
                        bgcolor=COLORS["accent"],
                        color="white",
                        on_click=self._resume_from_recovery
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )

            self.page.overlay.append(self._recovery_dialog)
            self._recovery_dialog.open = True
            self.page.update()

            self.log_msg(
                f"⚠️ Phát hiện phiên đăng bài bị gián đoạn ({summary['remaining']} nhóm còn lại)",
                color=COLORS["warning"])

        except Exception as e:
            log_error(f"Error checking recovery state: {e}")
            # Don't let recovery check errors block app startup
            recovery_manager.clear_recovery_state()

    def _dismiss_recovery(self, e):
        """User chose to skip recovery - clear state and continue fresh"""
        try:
            self._recovery_dialog.open = False
            self.page.update()
            recovery_manager.clear_recovery_state()
            self.log_msg("ℹ️ Đã bỏ qua phiên cũ. Bắt đầu mới.",
                         color=COLORS["text_muted"])
        except Exception as ex:
            log_error(f"Error dismissing recovery: {ex}")

    def _resume_from_recovery(self, e):
        """User chose to resume - restore content, images, and start posting"""
        try:
            self._recovery_dialog.open = False
            self.page.update()

            # Get remaining groups from recovery state
            remaining_groups = recovery_manager.get_remaining_groups()
            saved_content = recovery_manager.get_saved_content()
            saved_images = recovery_manager.get_saved_image_paths()
            summary = recovery_manager.get_summary()

            if not remaining_groups:
                self.log_msg("❌ Không tìm thấy nhóm còn lại để tiếp tục.",
                             color=COLORS["error"])
                recovery_manager.clear_recovery_state()
                return

            # Restore content to text field
            if saved_content:
                self.text_content.value = saved_content
                self.log_msg(
                    f"✅ Đã khôi phục nội dung bài viết ({len(saved_content)} ký tự)",
                    color=COLORS["success"])

            # Restore images
            if saved_images:
                self.image_paths = saved_images
                self.render_album_slots()
                self.log_msg(
                    f"✅ Đã khôi phục {len(saved_images)} ảnh đính kèm",
                    color=COLORS["success"])

            self.page.update()

            # Log resume info
            self.log_msg(
                f"🔄 Tiếp tục đăng bài từ phiên trước: {len(remaining_groups)} nhóm còn lại",
                color=COLORS["accent"])
            if summary:
                self.log_msg(
                    f"📊 Phiên trước: đã đăng {summary['posted']}/{summary['total']} nhóm",
                    color=COLORS["text_muted"], is_technical=True)

            # Clear recovery state BEFORE starting (will save new progress)
            recovery_manager.clear_recovery_state()

            # Start auto posting with recovered groups
            self._start_auto_with_groups(remaining_groups)

        except Exception as ex:
            log_error(f"Error resuming from recovery: {ex}")
            self.log_msg(
                f"❌ Lỗi khôi phục phiên: {str(ex)[:80]}",
                color=COLORS["error"])
            recovery_manager.clear_recovery_state()

    def _start_auto_with_groups(self, groups_to_post):
        """Start auto-posting with a specific list of groups (used for recovery resume)

        Args:
            groups_to_post: List of group dicts with 'name' and 'url' keys
        """
        import threading

        if auto_runner.is_running():
            self.show_snack("Auto is already running!",
                            color=COLORS["warning"])
            return

        # Validate: must have at least text or images
        post_content = self.text_content.value.strip() if self.text_content.value else ""
        has_content = bool(post_content)
        has_images = len(self.image_paths) > 0

        if not has_content and not has_images:
            self.show_snack("Vui lòng nhập nội dung hoặc thêm ảnh!",
                            color=COLORS["error"])
            self.log_msg(
                "❌ Không thể tiếp tục: không có nội dung và không có ảnh.",
                color=COLORS["error"])
            return

        # Use runner and guard
        auto_runner.can_start()
        mod_guard.set_automation_running(True)
        self.log_msg(
            f"✓ Tiếp tục đăng bài lên {len(groups_to_post)} nhóm...",
            color=COLORS["success"])
        self.show_snack(
            f"Resuming: posting to {len(groups_to_post)} remaining groups...",
            color=COLORS["success"])

        # Run in background thread
        thread = threading.Thread(
            target=self._run_auto_thread, args=(groups_to_post,), daemon=True)
        thread.start()

    def check_for_updates_async(self):
        """Check for updates in background (non-blocking)"""
        threading.Thread(target=self._check_updates_thread, daemon=True).start()

    def _check_updates_thread(self):
        """Background thread to check for updates"""
        try:
            time.sleep(2)  # Wait for UI to load first

            update_info = self.update_manager.check_for_updates()

            if update_info.get("has_update"):
                snack = ft.SnackBar(
                    ft.Text(f"✨ Update v{update_info['version']} available!"),
                    action="Update",
                    on_action=lambda e: self._show_update_dialog(update_info)
                )
                self.page.snack_bar = snack
                snack.open = True
                self.page.update()
                self.update_status_text.value = f"Update available: v{update_info['version']}"
                self.update_status_text.color = COLORS["success"]
            else:
                self.update_status_text.value = "Latest version"
                self.update_status_text.color = COLORS["text_muted"]

            self.page.update()
        except Exception as e:
            self.log_msg(
                f"Update check failed: {str(e)}", color=COLORS["warning"], is_technical=True)

    def manual_check_updates(self, e):
        """Manual update check when user clicks button"""
        if self.updating:
            self.log_msg("Update already in progress...",
                         color=COLORS["warning"])
            return

        if auto_runner.is_running():
            self.show_snack("⚠️ Không thể cập nhật khi đang Auto-Post!",
                            color=COLORS["warning"])
            self.log_msg("❌ Dừng Auto-Post trước khi thực hiện cập nhật.",
                         color=COLORS["warning"])
            return

        self.updating = True
        self.update_button.disabled = True
        self.update_status_text.value = "Checking..."
        self.update_status_text.color = COLORS["accent"]
        
        # Immediate feedback SnackBar (Request: "hiện lên luôn")
        snack = ft.SnackBar(ft.Text("🔍 Đang kiểm tra phiên bản mới..."))
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

        threading.Thread(target=self._perform_update_check, daemon=True).start()

    def _perform_update_check(self):
        """Perform update check in background"""
        try:
            update_info = self.update_manager.check_for_updates()

            if update_info.get("error"):
                self.log_msg(
                    f"❌ {update_info['error']}", color=COLORS["error"])
                self.update_status_text.value = "Check failed"
                self.update_status_text.color = COLORS["error"]
            elif update_info.get("has_update"):
                self.log_msg(
                    f"✨ New version available: v{update_info['version']}", color=COLORS["success"])
                self.update_status_text.value = f"v{update_info['version']} available"
                self.update_status_text.color = COLORS["success"]

                # Show update dialog
                self._show_update_dialog(update_info)
            else:
                self.log_msg(
                    f"✅ You're up to date (v{VERSION})", color=COLORS["success"])
                self.update_status_text.value = "Latest version"
                self.update_status_text.color = COLORS["text_muted"]

        except Exception as e:
            self.log_msg(
                f"❌ Update check failed: {str(e)}", color=COLORS["error"])
            self.update_status_text.value = "Check failed"
            self.update_status_text.color = COLORS["error"]

        finally:
            self.updating = False
            self.update_button.disabled = False
            self.page.update()

    def _show_update_dialog(self, update_info):
        """Update and show the PRE-ALLOCATED confirmation dialog"""
        def perform_update(e):
            self.update_dialog.open = False
            self.page.update()

            # Perform update in background via threading.Thread (User suggested "Nhát chém 1")
            threading.Thread(target=self._do_update, args=(update_info,), daemon=True).start()

        # Update the pre-allocated dialog content
        self.update_dialog.title = ft.Text(
            f"Update Available: v{update_info['version']}", color=COLORS["text_main"])
        
        self.update_dialog.content = ft.Column([
            ft.Text(f"Current version: v{VERSION}",
                    size=13, color=COLORS["text_muted"]),
            ft.Text(f"New version: v{update_info['version']}",
                    size=13, color=COLORS["success"]),
            ft.Divider(color=COLORS["border"]),
            ft.Text("Release notes:", size=12, weight="w500", color=COLORS["text_main"]),
            ft.Text(update_info.get("release_notes", "No notes available")[:300],
                    size=11, color=COLORS["text_muted"], max_lines=5)
        ], tight=True, spacing=10)
        
        self.update_dialog.actions = [
            ft.TextButton("Later", on_click=lambda e: (
                setattr(self.update_dialog, "open", False), self.page.update())),
            ft.ElevatedButton("Update Now", on_click=perform_update, bgcolor=COLORS["accent"])
        ]

        self.update_dialog.open = True
        self.page.update()

    def _do_update(self, update_info):
        """Perform the actual update with backup and rollback"""
        try:
            self.log_msg("🔄 Starting update process...",
                         color=COLORS["accent"])
            self.update_status_text.value = "Updating..."
            self.btn_check_update_menu.visible = False
            self.update_progress_container.visible = True
            self.page.update()

            # 1. Download update
            self.log_msg("📥 Downloading update...", color=COLORS["text_muted"])
            
            self.last_percent = -1
            def download_progress(downloaded, total):
                if total > 0:
                    percent = downloaded / total
                    current_pct = int(percent * 100)
                    if current_pct != self.last_percent:
                        self.last_percent = current_pct
                        self.update_progress_bar.value = percent
                        self.update_progress_text.value = f"Downloading v{update_info['version']}... {current_pct}%"
                        self.page.update()

            success, result = self.update_manager.download_update(
                update_info["download_url"], progress_callback=download_progress)

            if not success:
                self.log_msg(
                    f"❌ Download failed: {result}", color=COLORS["error"])
                self.update_status_text.value = "Download failed"
                self.update_status_text.color = COLORS["error"]
                self.update_progress_text.value = "Download failed"
                self.btn_check_update_menu.visible = True
                self.page.update()
                return

            self.log_msg("✅ Download complete", color=COLORS["success"])
            
            # 2. Trigger the "Relay Station" (.bat) update
            self.log_msg("🚀 Preparing update... App will restart shortly.", color=COLORS["success"])
            self.update_status_text.value = "Installing..."
            self.update_progress_text.value = "Launching updater..."
            self.page.update()
            
            time.sleep(1) # Let user see the message
            self._trigger_bat_updater(result)

        except Exception as e:
            self.log_msg(
                f"❌ Update failed with error: {str(e)}", color=COLORS["error"])
            self.update_status_text.value = "Update error"
            self.update_status_text.color = COLORS["error"]
            self.update_progress_text.value = "Update errored"
            self.update_progress_bar.color = COLORS["error"]
            self.btn_check_update_menu.visible = True
            self.page.update()

    def _trigger_bat_updater(self, zip_path):
        """Create and run a .bat script to perform the update while the app is closed (Nhát chém 3)"""
        import os
        import subprocess
        import sys
        
        # Ensure path is absolute for the .bat
        zip_abs = os.path.abspath(zip_path)
        app_exe = sys.executable if getattr(sys, 'frozen', False) else "AutoPostingTool.exe"
        app_name = os.path.basename(app_exe)
        
        # Use tar -xf which is built-in Windows 10/11
        bat_content = f"""@echo off
title AutoPostingTool Updater
echo ========================================
echo   AutoPostingTool is installing update  
echo ========================================
echo.
echo [1/3] Waiting for application to exit...
timeout /t 3 /nobreak >nul

echo [2/3] Extracting new files...
tar -xf "{zip_abs}" -C .

echo [3/3] Starting new version...
start "" "{app_name}"

echo.
echo Update complete! This window will close.
del "%~f0"
"""
        bat_path = "updater.bat"
        try:
            with open(bat_path, "w", encoding="ascii") as f:
                f.write(bat_content)
                
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([bat_path], creationflags=CREATE_NO_WINDOW if getattr(sys, 'frozen', False) else 0)
            
            # Suicide!
            os._exit(0)
        except Exception as e:
            self.log_msg(f"❌ Failed to launch updater: {e}", color=COLORS["error"])
            self.page.update()
