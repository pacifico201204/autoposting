"""
UI Handlers Module - Xử lý sự kiện và tương tác UI
Chịu trách nhiệm: Event handlers, dialog callbacks, log view management
"""

import os
from datetime import datetime
import flet as ft

# Import color scheme
from .ui_builder import COLORS


def switch_log_view(app_instance, view_type, btn_user, btn_technical):
    """Chuyển giữa User Messages và Technical Logs"""
    app_instance.current_log_view = view_type

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
        log_container = find_log_container(app_instance)
        if log_container:
            log_container.content = app_instance.log_list_user
    else:  # technical
        btn_technical.style = ft.ButtonStyle(
            color=COLORS["accent"],
            bgcolor=COLORS["bg_card"]
        )
        btn_user.style = ft.ButtonStyle(
            color=COLORS["text_muted"]
        )
        # Swap content container
        log_container = find_log_container(app_instance)
        if log_container:
            log_container.content = app_instance.log_list_technical

    app_instance.page.update()


def find_log_container(app_instance):
    """Tìm Container chứa log list"""
    if hasattr(app_instance, 'log_container_ref'):
        return app_instance.log_container_ref
    return None


def export_logs(app_instance, e):
    """Export logs thành file .txt"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"logs/vibecode_export_{timestamp}.txt"

    # Collect logs từ cả 2 views
    lines = []
    lines.append(
        f"=== VIBECODE AUTO LOGS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    lines.append(
        f"Total User Messages: {len(app_instance.log_list_user.controls)}")
    lines.append(
        f"Total Technical Logs: {len(app_instance.log_list_technical.controls)}\n")

    lines.append("--- USER MESSAGES ---")
    for control in reversed(app_instance.log_list_user.controls):
        if hasattr(control, 'content') and hasattr(control.content, 'value'):
            lines.append(control.content.value)

    lines.append("\n--- TECHNICAL LOGS ---")
    for control in reversed(app_instance.log_list_technical.controls):
        if hasattr(control, 'content') and hasattr(control.content, 'value'):
            lines.append(control.content.value)

    # Ghi vào file
    try:
        with open(export_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        app_instance.log_msg(
            f"✅ Exported logs: {export_filename}", color=COLORS["success"])
    except Exception as ex:
        app_instance.log_msg(
            f"❌ Failed to export: {str(ex)}", color=COLORS["error"])


def on_file_drop(app_instance, e):
    """Xử lý kéo thả file trực tiếp vào giao diện"""
    if hasattr(e, "files") and e.files:
        paths = [file.path for file in e.files]
    elif hasattr(e, "data") and e.data:
        import json
        try:
            data = json.loads(e.data)
            if isinstance(data, list):
                paths = [item.get("src") or item.get("path") for item in data]
            else:
                paths = []
        except Exception:
            paths = []
    else:
        paths = []

    added_count = 0
    for p in paths:
        if not p:
            continue
        import urllib.parse
        p = urllib.parse.unquote(p.replace("file://", ""))
        if os.path.isfile(p) and p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            if p not in app_instance.image_paths:
                app_instance.image_paths.append(p)
                added_count += 1

    if added_count > 0:
        app_instance.log_msg(
            f"✅ Đã thêm {added_count} ảnh từ Kéo Thả", color=COLORS["accent"])
        render_album_slots(app_instance)
        app_instance.page.update()


def render_album_slots(app_instance):
    """Cập nhật danh sách ảnh đính kèm"""
    if not hasattr(app_instance, 'attachment_list_container'):
        return

    app_instance.attachment_list_container.controls.clear()

    if not app_instance.image_paths:
        app_instance.attachment_list_container.controls.append(
            ft.Text("No images attached.",
                    color=COLORS["text_muted"], italic=True)
        )
    else:
        count = len(app_instance.image_paths)

        header_row = ft.Row([
            ft.Text(f"Attached {count} images:",
                    weight="bold", color=COLORS["success"]),
            ft.TextButton(
                "Clear All",
                icon=ft.Icons.DELETE,
                icon_color=COLORS["error"],
                on_click=lambda e: clear_all_images(app_instance)
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        app_instance.attachment_list_container.controls.append(header_row)

        for idx, path in enumerate(app_instance.image_paths):
            filename = os.path.basename(path)

            thumbnail = ft.Image(
                src=path,
                width=60,
                height=60,
                fit="cover",
                border_radius=8
            )

            item_row = ft.Container(
                content=ft.Row([
                    thumbnail,
                    ft.Text(filename, size=13, color=COLORS["text_main"],
                            expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=18,
                        icon_color=COLORS["error"],
                        on_click=create_remove_image_handler(app_instance, idx)
                    )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=5,
                border=ft.Border.all(1, COLORS["border"]),
                border_radius=8,
                bgcolor="#2A2B2D"
            )
            app_instance.attachment_list_container.controls.append(item_row)

    if getattr(app_instance, "page", None):
        app_instance.page.update()


def clear_all_images(app_instance):
    """Clear all attached images"""
    app_instance.image_paths.clear()
    render_album_slots(app_instance)
    app_instance.log_msg("✅ All images cleared")


def create_remove_image_handler(app_instance, idx):
    """Tạo handler cho nút xóa ảnh"""
    return lambda e: remove_image_at(app_instance, idx)


def remove_image_at(app_instance, idx):
    """Remove image at index"""
    if 0 <= idx < len(app_instance.image_paths):
        removed = app_instance.image_paths.pop(idx)
        app_instance.log_msg(f"✅ Image removed: {os.path.basename(removed)}")
        render_album_slots(app_instance)


def toggle_select_all_groups_handler(app_instance, e):
    """Toggle select all groups"""
    app_instance.is_all_selected = not app_instance.is_all_selected

    # Update button style
    if app_instance.is_all_selected:
        app_instance.btn_select_all.bgcolor = COLORS["accent"]
        app_instance.btn_select_all.color = "white"
    else:
        app_instance.btn_select_all.bgcolor = COLORS["border"]
        app_instance.btn_select_all.color = COLORS["text_main"]

    # Update all groups
    for idx, row in enumerate(app_instance.table_groups.rows):
        if hasattr(row, 'cells') and len(row.cells) > 0:
            checkbox = row.cells[0]
            if hasattr(checkbox, 'content') and hasattr(checkbox.content, 'value'):
                checkbox.content.value = app_instance.is_all_selected

    app_instance.page.update()


def open_add_group_dialog(app_instance, e):
    """Mở dialog thêm nhóm"""
    app_instance.page.dialog = app_instance.add_dialog
    app_instance.add_dialog.open = True
    app_instance.page.update()


def close_add_dialog(app_instance, e):
    """Đóng dialog thêm nhóm"""
    app_instance.add_dialog.open = False
    app_instance.add_name_input.value = ""
    app_instance.add_url_input.value = ""
    app_instance.page.update()


def open_settings_dialog(app_instance, e):
    """Mở dialog cài đặt"""
    app_instance.page.dialog = app_instance.settings_dialog
    app_instance.settings_dialog.open = True
    app_instance.page.update()


def close_settings_dialog(app_instance, e):
    """Đóng dialog cài đặt"""
    app_instance.settings_dialog.open = False
    app_instance.page.update()


def toggle_history_view(app_instance, e):
    """Chuyển giữa compose view và history view"""
    app_instance.post_compose_col.visible = not app_instance.post_compose_col.visible
    app_instance.post_history_col.visible = not app_instance.post_history_col.visible
    app_instance.page.update()


def show_snack(app_instance, message, color=COLORS["bg_card"]):
    """Hiển thị thông báo SnackBar - cải thiện UI"""
    # Determine text color based on background
    text_color = "white" if color in [
        COLORS["error"], COLORS["success"], COLORS["warning"], "#FF9800"] else "#000"

    app_instance.page.overlay.append(
        ft.SnackBar(
            ft.Text(message, color=text_color, size=14, weight="w500"),
            bgcolor=color,

            duration=3000,
            open=True
        )
    )
    app_instance.page.update()


def on_check_update(app_instance, e):
    """Handler for Check for Updates button"""
    try:
        from app_ui.update_manager import UpdateManager

        # Show progress
        app_instance.log_msg("🔄 Checking for updates...",
                             color=COLORS["text_muted"])

        update_mgr = UpdateManager()
        result = update_mgr.check_for_updates()

        if result.get("error"):
            app_instance.log_msg(
                f"❌ Check failed: {result['error']}", color=COLORS["error"])
            return

        if result.get("has_update"):
            # Update available
            new_version = result.get("version", "Unknown")
            current_version = update_mgr.current_version

            app_instance.log_msg(
                f"✅ Update available: {current_version} → {new_version}",
                color=COLORS["success"]
            )

            # Show release notes
            release_notes = result.get("release_notes", "No release notes")
            if release_notes:
                app_instance.log_msg(
                    f"📋 Release Notes:\n{release_notes[:200]}...",
                    color=COLORS["text_muted"]
                )

            # Backup before update
            app_instance.log_msg(
                "📦 Backing up current app...", color=COLORS["text_muted"])
            backup_success, backup_path = update_mgr.backup_current_app()

            if backup_success:
                app_instance.log_msg(
                    f"✅ Backup created: {backup_path}", color=COLORS["success"])

                # Start download
                app_instance.log_msg(
                    "⬇️ Downloading update...", color=COLORS["text_muted"])
                download_url = result.get("download_url")

                # For test mode, None URL means mock update
                if download_url is None and hasattr(update_mgr, 'test_mode') and update_mgr.test_mode:
                    download_success, download_file = update_mgr.download_update(
                        None,  # Mock download
                        progress_callback=lambda done, total:
                            app_instance.log_msg(
                                f"Downloaded: {done}/{total} bytes",
                                color=COLORS["text_muted"]
                            ) if total > 0 else None
                    )
                elif download_url:
                    download_success, download_file = update_mgr.download_update(
                        download_url,
                        progress_callback=lambda done, total:
                            app_instance.log_msg(
                                f"Downloaded: {done}/{total} bytes",
                                color=COLORS["text_muted"]
                            ) if total > 0 else None
                    )
                else:
                    app_instance.log_msg(
                        "⚠️ No download URL found in release",
                        color=COLORS["warning"]
                    )
                    return

                if download_success:
                    app_instance.log_msg(
                        f"✅ Download complete: {download_file}",
                        color=COLORS["success"]
                    )

                    # Extract update
                    app_instance.log_msg(
                        "📂 Extracting update...", color=COLORS["text_muted"])
                    extract_success, extract_msg = update_mgr.extract_update(
                        download_file)

                    if extract_success:
                        app_instance.log_msg(
                            f"✅ Update successful! {extract_msg}",
                            color=COLORS["success"]
                        )
                        app_instance.log_msg(
                            "🚀 AUTO-RESTART: Ứng dụng sẽ tự khởi động lại sau 5 giây để áp dụng bản cập nhật...",
                            color=COLORS["success"]
                        )
                        
                        # Wait and restart (5 seconds as requested)
                        import time
                        time.sleep(5)
                        from utils import restart_application
                        restart_application()
                    else:
                        app_instance.log_msg(
                            f"❌ Extraction failed: {extract_msg}",
                            color=COLORS["error"]
                        )
                        # Rollback
                        app_instance.log_msg(
                            "⚠️ Rolling back to previous version...", color=COLORS["warning"])
                        rollback_success, rollback_msg = update_mgr.restore_from_backup(
                            backup_path)
                        if rollback_success:
                            app_instance.log_msg(
                                f"✅ Rollback successful: {rollback_msg}",
                                color=COLORS["success"]
                            )
                else:
                    app_instance.log_msg(
                        f"❌ Download failed: {download_file}",
                        color=COLORS["error"]
                    )
            else:
                app_instance.log_msg(
                    f"❌ Backup failed: {backup_path}",
                    color=COLORS["error"]
                )
        else:
            # No update available
            current_version = update_mgr.current_version
            latest_version = result.get("version", "Unknown")
            app_instance.log_msg(
                f"✅ You are up to date! (v{current_version})",
                color=COLORS["success"]
            )

    except Exception as ex:
        app_instance.log_msg(
            f"❌ Update check error: {str(ex)}",
            color=COLORS["error"]
        )
