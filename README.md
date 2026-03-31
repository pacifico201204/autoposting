# Auto Posting Tool

**Tự động đăng bài lên Facebook với Playwright + Stealth Mode**

Auto-posting bot for Facebook groups with stealth mode to avoid account restrictions.

## ✨ Features

- ✅ **Auto-Post** - Tự động đăng bài theo lịch biểu
- ✅ **Multi-Group** - Đăng cùng lúc nhiều nhóm Facebook
- ✅ **Stealth Mode** - Tránh khóa tài khoản, bypass anti-bot
- ✅ **Image/Video** - Hỗ trợ ảnh và video
- ✅ **History** - Lưu lịch sử đăng bài

## 🚀 Quick Start

### Download Pre-built EXE (Recommended)
1. Go to [Releases](https://github.com/pacifico201204/autoposting/releases)
2. Download `AutoPostingTool-v1.0.zip`
3. Unzip and run `AutoPostingTool.exe`

**No Python or dependencies needed!**

### Run from Source (Developers)
```bash
pip install -r requirements.txt
python main.py
```

### View Documentation
- **[README.md](docs/README.md)** - Quick overview (1 min)
- **[CONFIG.md](docs/CONFIG.md)** - Setup & configuration (3 min)
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Errors & fixes (3 min)

## 📁 Project Structure

```
├── app_ui/                 # UI code (Flet)
│   ├── app_ui_main.py     # Main application
│   ├── ui_handlers.py     # Event handlers
│   └── ...
├── docs/                   # Documentation (3 files)
├── config.yaml            # Configuration (user-editable)
├── main.py                # Entry point
├── requirements.txt       # Dependencies
└── icon.ico               # App icon
```

## ⚙️ Requirements

- **Python:** 3.10+
- **OS:** Windows, macOS, Linux
- **Browser:** Chrome/Chromium (for Playwright)
- **Dependencies:** See `requirements.txt`

## 🔧 Build Distribution

```bash
# Create standalone exe
python -m PyInstaller Vibecode.spec

# Output: dist/Vibecode/Vibecode.exe
```

## 📊 Architecture

**Key Components:**
- `app_ui_main.py` - Main UI orchestrator
- `ui_history.py` - History management
- `ui_logging.py` - Logging system
- `anti_detection.py` - Stealth features
- `detection_limiter.py` - Rate limiting
- `storage.py` - Data persistence

**Design Pattern:**
- Modular managers (HistoryManager, LogManager)
- Config-driven (no hardcoding)
- Async support (Playwright + Flet)
- Thread-safe logging

## 🧪 Testing

```bash
# Run all tests
python test_comprehensive.py
python test_implementations.py
python test_backup_system.py

# Expected: 46/46 tests passing
```

## ⚠️ Warnings

- 🔴 **Ban Risk** - Use reasonable delays (30+ seconds)
- 🔴 **2FA** - Use App Password, not main password
- 🔴 **Terms of Service** - Respect Facebook ToS
- 🔴 **Spam** - Don't spam or post offensive content

## 📝 Configuration

Edit `config.yaml`:

```yaml
window:
  width: 1400
  height: 850

delays:
  post_min: 5    # Min delay (seconds)
  post_max: 10   # Max delay (seconds)

logging:
  max_history_items: 100
```

## 🛠️ Development

**Add Feature:**
1. Create new module in `app_ui/`
2. Initialize in `AppUI.__init__()`
3. Add tests
4. Update docs

**Code Standards:**
- PEP 8 style
- Type hints
- Docstrings
- 100% test coverage

## 📦 Release

To prepare for production release:

```bash
# Clean repo
rm -rf build/ dist/ logs/ temp_images/
rm groups.json fb_user_data_edge/

# Create venv & build
python -m venv venv
pip install -r requirements.txt
python -m PyInstaller Vibecode.spec

# Create release zip
# dist/Vibecode/ → Vibecode-v1.0.zip
```

## 🐛 Known Issues

- ⚠️ **Thread Safety** - Background threads (in progress)
- ⚠️ **Browser Crash** - Recoverable, auto-restart
- ⚠️ **Permission Error** - Fixed with fallback logging

## 📄 License

MIT License - See LICENSE file

## 🙋 Support

- Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
- Review `logs/vibecode.log` for errors
- Check `history.json` for posting status

---

**Made by Tristan**
