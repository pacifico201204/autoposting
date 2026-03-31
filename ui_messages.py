"""
User-friendly messages cho Vibecode Auto UI
Tất cả thông báo hiển thị cho user đều sử dụng file này
Technical logs vẫn được ghi vào file logs/ tách riêng
"""

# ✅ SUCCESS MESSAGES - Những thành công
MESSAGES = {
    # === STARTUP & INITIALIZATION ===
    "app_started": "✅ Ứng dụng đã sẵn sàng",
    "bot_ready": "🤖 Bot sẵn sàng! Chờ bạn thao tác",
    "browser_launched": "✅ Trình duyệt đã mở",
    "browser_connected": "✅ Kết nối trình duyệt thành công",
    "image_added": "✅ Đã thêm {count} ảnh",
    "clipboard_pasted": "✅ Dán ảnh từ clipboard thành công",
    
    # === AUTOMATION FLOW ===
    "auto_started": "✅ Bắt đầu đăng bài tự động",
    "waiting_login": "ℹ️ Đang chờ bạn đăng nhập vào Facebook\n⏱️ Thời gian: 2 phút",
    "page_loaded": "✅ Trang đã tải xong",
    "group_navigated": "✅ Đã chuyển đến nhóm: {group_name}",
    "text_typed": "✅ Đã nhập nội dung bài viết",
    "images_uploaded": "✅ Đã tải lên {count} ảnh",
    "post_submitted": "✅ Đã gửi bài viết",
    "dialog_closed": "✅ Đóng cửa sổ",
    
    # === PROGRESS & STATUS ===
    "processing_group": "⏳ Đang xử lý nhóm {current}/{total}: {group_name}",
    "waiting_post": "⏳ Chờ bài viết được xác nhận... ({remaining}s)",
    "random_delay": "⏳ Chờ {seconds}s trước nhóm tiếp theo",
    
    # === COMPLETION ===
    "auto_completed": "✅ Hoàn tất! Đã đăng bài lên {count} nhóm",
    "auto_stopped": "⏹️ Đã dừng tự động hóa",
    "auto_paused": "⏸️ Tạm dừng",
    
    # ===== ERRORS & WARNINGS =====
    "no_groups_selected": "❌ Vui lòng chọn ít nhất 1 nhóm",
    "no_images": "❌ Vui lòng thêm ít nhất 1 ảnh",
    "no_text": "❌ Vui lòng nhập nội dung bài viết",
    
    "network_error": "❌ Lỗi kết nối - Kiểm tra WiFi/Internet",
    "login_timeout": "❌ Hết thời gian chờ đăng nhập (2 phút)\n💡 Vui lòng đăng nhập và thử lại",
    "page_load_timeout": "❌ Trang tải quá lâu\n💡 Kiểm tra kết nối mạng",
    
    "group_navigation_failed": "❌ Không thể mở nhóm: {group_name}\n💡 Kiểm tra URL hoặc quyền truy cập",
    "input_box_not_found": "❌ Không tìm được khung nhập bài\n💡 Facebook có thể thay đổi giao diện",
    "post_button_not_found": "❌ Không tìm được nút 'Đăng'\n💡 Thử lại...",
    "upload_failed": "❌ Tải ảnh thất bại\n💡 Kiểm tra kích thước ảnh (dưới 4MB)",
    
    "group_skipped": "⚠️ Bỏ qua nhóm: {group_name}\n💡 Sẽ thử lại nhóm tiếp theo",
    "retry_attempt": "🔄 Thử lại ({attempt}/3)...",
    
    # === SETTINGS & CONFIG ===
    "delay_updated": "✅ Cập nhật thời gian trễ: {min}s - {max}s",
    "settings_saved": "✅ Đã lưu cài đặt",
    "group_added": "✅ Đã thêm nhóm: {group_name}",
    "group_deleted": "✅ Đã xoá nhóm: {group_name}",
}

# Log levels cho technical logs (file logs)
LOG_LEVELS = {
    "DEBUG": "🔍",   # Chi tiết kỹ thuật
    "INFO": "ℹ️",    # Thông tin quan trọng
    "WARNING": "⚠️",  # Cảnh báo
    "ERROR": "❌",   # Lỗi
    "CRITICAL": "🚨", # Lỗi nghiêm trọng
}

def get_message(key, **kwargs):
    """
    Lấy message từ dictionary, replace biến {var_name}
    
    Ví dụ:
        get_message("processing_group", current=2, total=5, group_name="Dev Vietnam")
        → "⏳ Đang xử lý nhóm 2/5: Dev Vietnam"
    """
    if key not in MESSAGES:
        return f"⚠️ Unknown message: {key}"
    
    msg = MESSAGES[key]
    try:
        return msg.format(**kwargs)
    except KeyError as e:
        return f"⚠️ Missing parameter: {e}"

# Emoticon colors mapping
MESSAGE_COLORS = {
    "✅": "#31A24C",   # Xanh lá (success)
    "❌": "#F02849",   # Đỏ (error)
    "⏳": "#F5A623",   # Vàng (warning/progress)
    "⚠️": "#F5A623",   # Vàng (warning)
    "ℹ️": "#1877F2",   # Xanh dương (info)
    "⏹️": "#B0B3B8",   # Xám (neutral)
    "⏸️": "#B0B3B8",   # Xám (neutral)
    "🔄": "#1877F2",   # Xanh dương (retry)
    "🔍": "#1877F2",   # Xanh dương (debug)
    "🚨": "#F02849",   # Đỏ (critical)
}

def get_message_color(message):
    """
    Trả về màu sắc dựa trên emoticon đầu tiên của message
    """
    for emoji, color in MESSAGE_COLORS.items():
        if emoji in message:
            return color
    return "#E4E6EB"  # Default: text_main color


# ============================================================================
# HƯỚNG DẪN: Những logs nào nên hiển thị ở "User Messages" tab?
# ============================================================================
# 
# ✅ NÊN HIỂN THỊ (User Messages):
# • Khởi động / Kết thúc:
#   - "Bot sẵn sàng! Chờ bạn thao tác"
#   - "Bắt đầu đăng bài tự động"
#   - "Hoàn tất! Đã đăng bài lên X nhóm"
#   - "Đã dừng tự động hóa"
#
# • Tiến trình quan trọng:
#   - "Đang chờ bạn đăng nhập vào Facebook (2 phút)"
#   - "Đang xử lý nhóm X/Y: Tên nhóm"
#   - "Trang đã tải xong"
#   - "Đã chuyển đến nhóm: Tên nhóm"
#   - "Đã nhập nội dung bài viết"
#   - "Đã tải lên X ảnh"
#   - "Đã gửi bài viết"
#
# • Thông tin chờ:
#   - "Chờ bài viết được xác nhận... (8s)"
#   - "Chờ 7s trước nhóm tiếp theo"  (hiển thị 1 lần, không update liên tục)
#
# • Cảnh báo / Lỗi:
#   - "❌ Không tìm được khung nhập bài"
#   - "❌ Lỗi kết nối - Kiểm tra WiFi/Internet"
#   - "⚠️ Bỏ qua nhóm: Tên nhóm"
#
# • Cài đặt:
#   - "✅ Thêm nhóm: Tên nhóm"
#   - "✅ Cập nhật thời gian trễ: 5s - 10s"
#
# ❌ KHÔNG NÊN HIỂN THỊ (Technical Logs only):
# • Chi tiết selector:
#   - "Found post input by method 3: aria-label"
#   - "Trying selector: div[contenteditable=true]"
#
# • Trạng thái nội bộ:
#   - "Page URL: https://facebook.com/groups/..."
#   - "Stealth mode applied"
#   - "Keyboard press: Control+Enter"
#
# • Debug messages:
#   - "Retry attempt 2/3"
#   - "Context check passed"
#   - "Screenshot saved: error_group_20260330_190523.png"
#
# Quy tắc:
# • User log = Thích hợp cho người không kỹ thuật
# • Technical log = Chi tiết cho debugging & developer
# ============================================================================
