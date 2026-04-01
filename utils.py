"""
Shared Utilities Module
Consolidates common functions used across multiple modules.
"""

import os
import sys
import subprocess


def get_resource_path(filename):
    """Get correct path for bundled READ-ONLY resources (PyInstaller or development).

    When running as a PyInstaller bundle, resources are extracted to sys._MEIPASS.
    In development mode, resources are relative to the project root directory.

    Use this for: icon.ico, config.yaml (template only)
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundled EXE
        base_path = sys._MEIPASS
    else:
        # Running in development mode - always use project root
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


def get_app_dir():
    """Get the application root directory (where the .exe is)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_writable_path(filename):
    """Get path for writable files (data, config, logs).

    FOR v1.3.25+: Everything is hidden inside the '_internal' folder 
    to keep the root directory clean (only EXE visible).

    Args:
        filename: Name of the file (e.g., 'groups.json')

    Returns:
        Absolute path pointing to the file inside _internal folder
    """
    if getattr(sys, 'frozen', False):
        # In PyInstaller 6+ onedir, _internal stores all data.
        # We place our writable files there to hide them from user.
        target_dir = os.path.join(get_app_dir(), "_internal")
        # Ensure directory exists (it should, but safety first)
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except:
                return os.path.join(get_app_dir(), filename) # Fallback to root if locked
        return os.path.join(target_dir, filename)
    else:
        # Development mode
        return os.path.join(get_app_dir(), filename)


def restart_application(page=None):
    """Restart the application with Detached Process and immediate exit."""
    try:
        if getattr(sys, 'frozen', False):
            # EXE mode
            executable = sys.executable
            # Mở app mới ở chế độ độc lập (detached)
            subprocess.Popen(
                [executable],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            # Python script mode
            executable = sys.executable
            script = sys.argv[0]
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(
                [executable, script],
                creationflags=flags,
                close_fds=True
            )
            
        # Tắt nóng giao diện Flet cũ
        if page:
            try:
                page.window.destroy()
            except Exception:
                pass
                
        # Ép tiến trình Python cũ "tự sát" ngay lập tức
        os._exit(0) 
    except Exception as e:
        print(f"Failed to restart: {e}")
        os._exit(1)
