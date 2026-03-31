import json
import os
from logger_config import log_error

DATA_FILE = "groups.json"


def load_groups():
    """Tải dữ liệu danh sách Group từ file JSON."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Lỗi khi đọc file groups.json: {e}")
        return []


def save_groups(data):
    """Lưu dữ liệu danh sách Group xuống file JSON."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        log_error(f"Lỗi khi ghi file DB: {e}")
