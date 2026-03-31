"""
UI Builder Module - Xây dựng giao diện Flet
Chịu trách nhiệm: Build layout, cards, dialogs, UI components
"""

import flet as ft

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

FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def make_card(title, content, expand=False, padding=15):
    """Hàm dựng các hộp nội dung (Cards) nhất quán"""
    container = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text(title, weight="bold", size=16,
                                color=COLORS["text_main"], text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center,
                expand=True
            ),
            ft.Divider(color=COLORS["border"], height=1),
            content
        ], spacing=15, expand=expand),
        padding=padding,
        bgcolor=COLORS["bg_card"],
        border_radius=12,
        border=ft.Border.all(1, COLORS["border"]
                             ) if COLORS["border"] else None,
        expand=expand,
        margin=ft.margin.only(bottom=15)
    )
    return container


def make_menu_item(icon, text, color, on_click):
    """Tạo nút menu bên trái phong cách Facebook"""
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, size=20, color=color),
                ft.Text(text, size=14, weight="w500",
                        color=COLORS["text_main"], expand=True)
            ],
            spacing=10,
            alignment="start"
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        border_radius=8,
        bgcolor=COLORS["bg_card"],
        on_hover=lambda e: on_menu_hover(e, color),
        on_click=on_click,
        ink=True
    )


def on_menu_hover(e, color):
    """Xử lý hover state cho menu items"""
    if e.data == "true":  # Hover in
        e.control.bgcolor = COLORS["border"]
    else:  # Hover out
        e.control.bgcolor = COLORS["bg_card"]
    e.control.update()


def build_header():
    """Xây dựng header bar"""
    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.FACEBOOK, color=COLORS["accent"], size=40),
                ft.Text("Auto Posting by Tristan", size=24,
                        weight="w800", color=COLORS["text_main"])
            ], spacing=10),
            ft.Container(expand=True),  # Khoảng trống giữa
        ], alignment="spaceBetween", vertical_alignment="center"),
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        bgcolor=COLORS["bg_card"],
        border=ft.Border(bottom=ft.BorderSide(1, COLORS["border"]))
    )
    return header


def build_left_menu(start_auto_cb, stop_auto_cb, add_group_cb, settings_cb, history_cb):
    """Xây dựng menu bên trái"""
    menu_items = ft.Column([
        make_menu_item(ft.Icons.ROCKET_LAUNCH, "Start Auto",
                       COLORS["accent"], start_auto_cb),
        make_menu_item(ft.Icons.STOP_CIRCLE, "Stop",
                       COLORS["error"], stop_auto_cb),
        ft.Divider(color=COLORS["border"]),
        make_menu_item(ft.Icons.GROUP_ADD, "Add Group",
                       COLORS["success"], add_group_cb),
        make_menu_item(ft.Icons.SETTINGS, "Delay",
                       COLORS["text_main"], settings_cb),
        make_menu_item(ft.Icons.HISTORY, "History",
                       COLORS["text_main"], history_cb),
    ], spacing=5)

    col_left = ft.Container(
        content=menu_items,
        padding=20,
        expand=2
    )
    return col_left


def build_center_compose():
    """Xây dựng cột giữa - soạn thảo bài đăng"""
    # 1. Text input
    text_content = ft.TextField(
        multiline=True,
        min_lines=12, max_lines=20,
        expand=True,
        hint_text="Nhập nội dung bài viết quảng cáo của bạn...",
        border_color="transparent",
        focused_border_color="transparent",
        bgcolor=COLORS["bg_card"],
        text_size=16,
        color=COLORS["text_main"],
        cursor_color=COLORS["accent"],
        height=300
    )
    card_content = make_card("Create Post", ft.Column(
        [text_content], expand=True), expand=False)

    # 2. Image paste button
    btn_paste_image = ft.ElevatedButton(
        "PASTE IMAGE FROM CLIPBOARD",
        icon=ft.Icons.CONTENT_PASTE,
        color="#ffffff",
        bgcolor="#1877F2",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
        ),
        height=50,
        expand=True,
    )

    attachment_list_container = ft.Column(spacing=5)
    album_controls = ft.Column(
        [
            ft.Row([btn_paste_image], expand=True),
            attachment_list_container,
        ],
        spacing=15,
    )

    card_image = make_card("Attached Media", album_controls, expand=False)
    post_compose_col = ft.Column(
        [card_content, card_image], scroll="adaptive", expand=True)

    # 3. History view (initially hidden)
    history_list_view = ft.ListView(expand=True, spacing=10, auto_scroll=False)
    btn_back_home = ft.ElevatedButton(
        "Back to Dashboard",
        icon=ft.Icons.ARROW_BACK,
        bgcolor=COLORS["border"],
        color=COLORS["text_main"],
    )

    history_header = ft.Row([
        ft.Text("Post History", size=20, weight="bold",
                color=COLORS["text_main"]),
        btn_back_home
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    post_history_col = ft.Column([
        history_header,
        ft.Divider(color=COLORS["border"]),
        history_list_view
    ], expand=True, visible=False)

    col_center = ft.Container(
        content=ft.Stack([
            post_compose_col,
            post_history_col
        ], expand=True),
        padding=ft.padding.only(top=20, left=10, right=10, bottom=20),
        expand=5
    )

    return {
        "col_center": col_center,
        "text_content": text_content,
        "btn_paste_image": btn_paste_image,
        "attachment_list_container": attachment_list_container,
        "post_compose_col": post_compose_col,
        "post_history_col": post_history_col,
        "history_list_view": history_list_view,
        "btn_back_home": btn_back_home,
    }


def build_right_panel(toggle_log_view_cb, export_logs_cb):
    """Xây dựng cột phải - groups table và activity logs"""
    # 1. Groups table
    btn_select_all = ft.ElevatedButton(
        "ALL",
        color=COLORS["text_main"],
        bgcolor=COLORS["border"],
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.padding.symmetric(horizontal=15, vertical=0),
        ),
        height=30
    )

    table_groups = ft.DataTable(
        columns=[
            ft.DataColumn(
                ft.Row([btn_select_all], alignment="start")
            ),
        ],
        rows=[],
        heading_row_height=40,
        data_row_min_height=40,
        data_row_max_height=40,
        show_checkbox_column=False,
        heading_row_color="transparent",
        expand=True
    )

    card_groups = make_card("Groups List", ft.Container(
        content=ft.Column([table_groups], scroll="auto", expand=True),
        border_radius=8, bgcolor=COLORS["bg_card"],
        expand=True
    ), expand=True)

    # 2. Activity logs with toggle
    log_list_user = ft.ListView(expand=True, auto_scroll=False, spacing=5)
    log_list_technical = ft.ListView(expand=True, auto_scroll=False, spacing=5)

    btn_user_messages = ft.TextButton(
        "User Messages",
    )
    btn_technical_logs = ft.TextButton(
        "Technical Logs",
    )

    toggle_row = ft.Container(
        content=ft.Row([
            btn_user_messages,
            btn_technical_logs,
            ft.Container(expand=True),
            ft.IconButton(
                ft.Icons.FILE_DOWNLOAD_OUTLINED,
                tooltip="Export logs",
                on_click=export_logs_cb,
                icon_color=COLORS["text_muted"]
            )
        ], alignment="spaceBetween", vertical_alignment="center"),
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border_radius=ft.border_radius.vertical(top=8),
        bgcolor=COLORS["bg_card"],
        border=ft.Border(bottom=ft.BorderSide(1, COLORS["border"]))
    )

    log_container = ft.Container(
        content=log_list_user, expand=True, padding=10,
        border_radius=ft.border_radius.vertical(bottom=8),
        bgcolor=COLORS["bg_main"]
    )

    card_logs = make_card(
        "Activity Logs",
        ft.Column([toggle_row, log_container], expand=True, spacing=0),
        padding=0,
        expand=True
    )

    col_right = ft.Container(
        content=ft.Column([card_groups, card_logs], expand=True),
        padding=ft.padding.only(top=20, left=10, right=20, bottom=20),
        expand=3
    )

    return {
        "col_right": col_right,
        "btn_select_all": btn_select_all,
        "table_groups": table_groups,
        "log_list_user": log_list_user,
        "log_list_technical": log_list_technical,
        "btn_user_messages": btn_user_messages,
        "btn_technical_logs": btn_technical_logs,
        "log_container_ref": log_container,
        "toggle_row": toggle_row,
    }


def build_dialogs():
    """Xây dựng các dialog (add group, settings)"""
    # Add group dialog
    add_name_input = ft.TextField(
        label="Group Name", border_color=COLORS["border"], color=COLORS["text_main"])
    add_url_input = ft.TextField(
        label="Group URL", border_color=COLORS["border"], color=COLORS["text_main"])
    add_dialog = ft.AlertDialog(
        title=ft.Text("Add New Group", color=COLORS["text_main"]),
        bgcolor=COLORS["bg_card"],
        content=ft.Column([add_name_input, add_url_input], tight=True),
        actions=[
            ft.TextButton("Cancel", style=ft.ButtonStyle(
                color=COLORS["text_muted"])),
            ft.TextButton("Save", style=ft.ButtonStyle(color=COLORS["accent"]))
        ]
    )

    # Settings dialog
    delay_min_input = ft.TextField(
        label="From (seconds)",
        value="5",
        border_color=COLORS["border"],
        color=COLORS["text_main"],
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120
    )
    delay_max_input = ft.TextField(
        label="To (seconds)",
        value="10",
        border_color=COLORS["border"],
        color=COLORS["text_main"],
        keyboard_type=ft.KeyboardType.NUMBER,
        width=120
    )
    settings_dialog = ft.AlertDialog(
        title=ft.Text("Random Delay Settings", color=COLORS["text_main"]),
        bgcolor=COLORS["bg_card"],
        content=ft.Column([
            ft.Row([delay_min_input, ft.Text(
                "-", color=COLORS["text_main"]), delay_max_input]),
            ft.Text("Random wait time between posts (seconds)",
                    color=COLORS["text_muted"], size=12)
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", style=ft.ButtonStyle(
                color=COLORS["text_muted"])),
            ft.TextButton("Save", style=ft.ButtonStyle(color=COLORS["accent"]))
        ]
    )

    return {
        "add_dialog": add_dialog,
        "add_name_input": add_name_input,
        "add_url_input": add_url_input,
        "settings_dialog": settings_dialog,
        "delay_min_input": delay_min_input,
        "delay_max_input": delay_max_input,
    }
