"""
Media Manager Module - Quản lý ảnh/media
Chịu trách nhiệm: Upload ảnh, paste từ clipboard, render preview
"""

import os
from PIL import ImageGrab
import flet as ft
from .ui_builder import COLORS
from . import ui_handlers


async def paste_image_from_clipboard(app_instance, e):
    """Dán ảnh từ clipboard"""
    try:
        # Lấy ảnh từ clipboard
        img = ImageGrab.grabclipboard()
        
        if img is None:
            app_instance.log_msg("❌ Clipboard không có ảnh. Vui lòng copy ảnh trước!", color=COLORS["error"])
            return
        
        # Tạo thư mục nếu chưa tồn tại
        temp_dir = "temp_images"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Lưu ảnh tạm thời
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join(temp_dir, f"clipboard_{timestamp}.png")
        img.save(temp_path, "PNG")
        
        # Thêm vào danh sách
        if temp_path not in app_instance.image_paths:
            app_instance.image_paths.append(temp_path)
            app_instance.log_msg("✅ Dán ảnh từ clipboard thành công", color=COLORS["success"])
            ui_handlers.render_album_slots(app_instance)
            app_instance.page.update()
        else:
            app_instance.log_msg("⚠️ Ảnh này đã tồn tại trong danh sách", color=COLORS["warning"])
            
    except Exception as ex:
        app_instance.log_msg(f"❌ Lỗi paste ảnh: {str(ex)}", color=COLORS["error"])


def on_image_path_submitted(app_instance, e):
    """Nhận đường dẫn ảnh từ input field"""
    path = app_instance.image_path_input.value.strip()
    
    if not path:
        return
    
    if os.path.isfile(path) and path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        if path not in app_instance.image_paths:
            app_instance.image_paths.append(path)
            app_instance.log_msg(f"✅ Đã thêm ảnh: {os.path.basename(path)}", color=COLORS["success"])
            ui_handlers.render_album_slots(app_instance)
            app_instance.image_path_input.value = ""
            app_instance.page.update()
        else:
            app_instance.log_msg("⚠️ Ảnh này đã có trong danh sách", color=COLORS["warning"])
    else:
        app_instance.log_msg("❌ Đường dẫn không hợp lệ hoặc không phải ảnh", color=COLORS["error"])


def db_config_click(app_instance, e):
    """Placeholder for database config"""
    pass
