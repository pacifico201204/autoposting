# 🚀 AutoPostingTool (Vibecode Release)

**AutoPostingTool** là giải pháp tự động hóa đăng bài mạng xã hội mạnh mẽ, được thiết kế với sự chú trọng đặc biệt vào khả năng vượt qua các hệ thống phát hiện bot (Stealth) và trải nghiệm người dùng hiện đại.

## ✨ Tính Năng Nổi Bật (v1.4)

### 🤖 Động Cơ Đăng Bài Thông Minh
- **Đa tài khoản & Nhóm:** Quản lý và đăng nội dung lên hàng loạt hội nhóm thông qua danh sách JSON linh hoạt.
- **Retry Logic:** Tự động thử lại khi gặp lỗi kết nối hoặc bị chặn tạm thời.
- **Hỗ trợ Media:** Đính kèm ảnh đa dạng với cơ chế album chuyên nghiệp.

### 🛡️ Công Nghệ Chống Phát Hiện (Stealth & Anti-Bot)
- **Playwright-Stealth:** Tích hợp sâu các kỹ thuật làm giả dấu vân tay trình duyệt (Canvas, WebGL, v.v.).
- **Randomization:** Ngẫu nhiên hóa hành vi di chuột, tốc độ gõ phím và User-Agent để mô phỏng người thật 100%.
- **Detection Limiter:** Tự động ngắt kết nối khi chạm ngưỡng giới hạn đăng bài trong phiên hoặc trong ngày để bảo vệ tài khoản.

### 🎨 Giao Diện Hiện Đại (Glassmorphism)
- **Flet Framework:** UI siêu mượt mà, hỗ trợ Dark Mode và bố cục Responsive.
- **Dual Logs:** Phân tách rõ ràng giữa **Thông báo người dùng** (Dễ hiểu) và **Log kỹ thuật** (Chi tiết để debug).
- **Update Dialog:** Thông báo và thực hiện cập nhật ngay trong ứng dụng.

### 🔄 Hệ Thống Cập Nhật & Phục Hồi "Nồi Đồng Cối Đá"
- **PowerShell Relay Updater:** Cơ chế cập nhật độc lập thông qua script PowerShell với vòng lặp retry, đảm bảo cài đặt thành công ngay cả khi file bị khóa.
- **Recovery Manager:** Tự động sao lưu cấu hình (`config.yaml`) và dữ liệu trước khi thay đổi hệ thống.
- **Auto-Cleanup:** Tự dọn dẹp các tệp tin thừa (`.old`, `.bak`) sau khi cập nhật thành công.

## 🛠️ Cài đặt & Sử dụng
- **Phát triển:** `python main.py`
- **Build EXE:** Sử dụng `AutoPostingTool.spec` với PyInstaller.
- **Cấu hình:** Chỉnh sửa các ngưỡng giới hạn tại `config.yaml`.

## 📈 Lịch sử phiên bản
- **v1.4.0:** Bước nhảy vọt về độ ổn định với bộ cập nhật PowerShell mới và tối ưu hóa hiệu năng UI.
- **v1.3.x:** Hoàn thiện hệ thống Anti-bot và quản lý nhóm.

---
*Phát triển bởi Tristan.*
