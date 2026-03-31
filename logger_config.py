"""
Logger configuration cho Auto Posting
Lưu logs vào file + console cùng lúc
Tự động rotate logs khi quá lớn
"""

import logging
import logging.handlers
import os
from datetime import datetime

# Tạo thư mục logs nếu chưa tồn tại
LOG_DIR = "logs"
try:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
except PermissionError:
    print(f"⚠️ Warning: Cannot create logs directory at {LOG_DIR}")
    LOG_DIR = "."  # Fallback to current directory if logs dir locked
except Exception as e:
    print(f"⚠️ Warning: Error with logs directory: {e}")
    LOG_DIR = "."  # Fallback to current directory

# Use fixed filename for effective log rotation
log_filename = os.path.join(LOG_DIR, "autoposting.log")

# Cấu hình logger
logger = logging.getLogger("autoposting_app")
logger.setLevel(logging.DEBUG)

# Format cho logs
log_format = logging.Formatter(
    fmt='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler ghi file với rotation (DEBUG level)
# RotatingFileHandler: max 5MB per file, keep 5 backups (25MB total)
try:
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,  # Keep 5 backups
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"⚠️ Warning: Cannot create log file: {e}")
    # Continue without file logging

# Handler console (INFO level)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)


def get_logger():
    """Trả về logger instance"""
    return logger


def log_debug(msg):
    """Debug level - chỉ ghi vào file"""
    logger.debug(msg)


def log_info(msg):
    """Info level - ghi vào file + console"""
    logger.info(msg)


def log_warning(msg):
    """Warning level"""
    logger.warning(msg)


def log_error(msg):
    """Error level"""
    logger.error(msg)


def log_exception(msg, exc):
    """Log exception chi tiết"""
    logger.exception(f"{msg}: {str(exc)}")
