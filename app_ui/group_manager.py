"""
Group Manager Module - Quản lý nhóm Facebook
Chịu trách nhiệm: Load/save groups, toggle selection, add/delete groups
"""

import flet as ft
from storage import save_groups
from .ui_builder import COLORS


def populate_groups(app_instance):
    """Tải nhóm vào bảng"""
    app_instance.table_groups.rows.clear()
    
    # Sync checkbox state nếu trống
    if not app_instance.groups_data:
        app_instance.is_all_selected = False
        app_instance.btn_select_all.bgcolor = COLORS["border"]
        app_instance.btn_select_all.color = COLORS["text_main"]

    for idx, group in enumerate(app_instance.groups_data):
        name = group.get("name", "")
        is_selected = group.get("selected", False)
        
        cb = ft.Checkbox(
            value=is_selected,
            on_change=create_toggle_group_handler(app_instance, idx),
            fill_color={
                ft.ControlState.HOVERED: COLORS["border"],
                ft.ControlState.FOCUSED: COLORS["border"],
                ft.ControlState.DEFAULT: COLORS["accent"] if is_selected else "transparent",
                ft.ControlState.SELECTED: COLORS["accent"]
            },
            check_color=COLORS["text_main"]
        )
        
        row_content = ft.Row([
            cb,
            ft.Text(name, color=COLORS["text_main"], size=13, tooltip=group.get("url", ""), expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_size=18,
                icon_color=COLORS["error"],
                tooltip="Xóa",
                on_click=create_delete_handler(app_instance, idx)
            )
        ])
        
        app_instance.table_groups.rows.append(
            ft.DataRow(cells=[ft.DataCell(row_content)])
        )
    
    app_instance.page.update()


def toggle_select_all_groups(app_instance, e):
    """Toggle chọn tất cả nhóm"""
    app_instance.is_all_selected = not app_instance.is_all_selected
    
    # Update button style
    if app_instance.is_all_selected:
        app_instance.btn_select_all.bgcolor = COLORS["accent"]
        app_instance.btn_select_all.color = "white"
    else:
        app_instance.btn_select_all.bgcolor = COLORS["border"]
        app_instance.btn_select_all.color = COLORS["text_main"]

    for group in app_instance.groups_data:
        group["selected"] = app_instance.is_all_selected
    
    populate_groups(app_instance)


def create_toggle_group_handler(app_instance, idx):
    """Tạo handler cho toggle group"""
    return lambda e: toggle_single_group(app_instance, idx, e.control.value)


def toggle_single_group(app_instance, idx, is_checked):
    """Toggle selection cho một nhóm"""
    if 0 <= idx < len(app_instance.groups_data):
        app_instance.groups_data[idx]["selected"] = is_checked
        
        # Update 'select all' button based on individual items
        all_selected = all(g.get("selected", False) for g in app_instance.groups_data)
        app_instance.is_all_selected = all_selected
        
        if app_instance.is_all_selected:
            app_instance.btn_select_all.bgcolor = COLORS["accent"]
            app_instance.btn_select_all.color = "white"
        else:
            app_instance.btn_select_all.bgcolor = COLORS["border"]
            app_instance.btn_select_all.color = COLORS["text_main"]
        
        app_instance.page.update()


def create_delete_handler(app_instance, idx):
    """Tạo handler cho nút xóa nhóm"""
    return lambda e: delete_group(app_instance, idx)


def delete_group(app_instance, idx):
    """Xóa nhóm"""
    if 0 <= idx < len(app_instance.groups_data):
        deleted = app_instance.groups_data.pop(idx)
        save_groups(app_instance.groups_data)
        app_instance.log_msg(f"❌ Đã xóa nhóm: {deleted.get('name', '')}", color=COLORS["error"])
        populate_groups(app_instance)


def confirm_add_group(app_instance, e):
    """Confirm thêm nhóm mới"""
    name = app_instance.add_name_input.value.strip()
    url = app_instance.add_url_input.value.strip()
    
    if name and url:
        add_group_to_table(app_instance, name, url)
        close_add_dialog(app_instance, None)
    else:
        app_instance.log_msg("❌ Vui lòng nhập đầy đủ Tên nhóm và URL", color=COLORS["error"])


def add_group_to_table(app_instance, name, url):
    """Thêm nhóm vào bảng"""
    app_instance.groups_data.append({"name": name, "url": url, "selected": False})
    save_groups(app_instance.groups_data)
    app_instance.log_msg(f"✅ Đã thêm nhóm: {name}", color=COLORS["success"])
    populate_groups(app_instance)


def close_add_dialog(app_instance, e):
    """Đóng dialog thêm nhóm"""
    app_instance.add_dialog.open = False
    app_instance.add_name_input.value = ""
    app_instance.add_url_input.value = ""
    app_instance.page.update()


def confirm_settings(app_instance, e):
    """Confirm cài đặt delay"""
    try:
        val_min = int(app_instance.delay_min_input.value)
        val_max = int(app_instance.delay_max_input.value)
        
        if val_min < 0:
            val_min = 0
        if val_max < val_min:
            val_max = val_min
        
        app_instance.post_delay_min = val_min
        app_instance.post_delay_max = val_max
        app_instance.log_msg(
            f"✅ Đã lưu thời gian delay: {app_instance.post_delay_min}s - {app_instance.post_delay_max}s",
            color=COLORS["success"]
        )
        close_settings_dialog(app_instance, e)
    except ValueError:
        app_instance.log_msg("❌ Vui lòng nhập số nguyên cho Delay!", color=COLORS["error"])


def close_settings_dialog(app_instance, e):
    """Đóng dialog cài đặt"""
    app_instance.settings_dialog.open = False
    app_instance.page.update()


def get_selected_groups(app_instance):
    """Lấy danh sách nhóm đã chọn"""
    return [g for g in app_instance.groups_data if g.get("selected")]
