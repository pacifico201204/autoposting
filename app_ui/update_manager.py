"""
Update Manager - Handle app updates, backups, and rollback
Features:
  - Check for new releases on GitHub
  - Auto-backup before update
  - Download and extract new version
  - Rollback to previous version if update fails
"""

import os
import shutil
import zipfile
import requests
from datetime import datetime
from pathlib import Path
from logger_config import log_debug, log_info, log_error
from utils import get_writable_path, get_app_dir

# App Version
APP_VERSION = "1.3.31"
GITHUB_REPO = "pacifico201204/autoposting"
# Put backups NEXT TO exe folder for safety during restore
BACKUP_FOLDER = os.path.join(os.path.dirname(get_app_dir()), "AutoPostingTool_Backups")


class UpdateManager:
    def __init__(self):
        self.current_version = APP_VERSION
        self.backup_folder = Path(BACKUP_FOLDER)
        try:
            self.backup_folder.mkdir(exist_ok=True)
        except Exception as e:
            log_error(f"Failed to create backup folder: {e}")
            # Continue anyway, backup just won't work
        self.app_folder = Path(get_app_dir())

    def check_for_updates(self) -> dict:
        """
        Check GitHub for latest release
        Returns: {"has_update": bool, "version": str, "download_url": str}
        """
        try:
            response = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            latest_version = data.get("tag_name", "").lstrip("v")

            # Compare versions
            if self._compare_versions(latest_version, self.current_version) > 0:
                # Get download URL for zip file
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".zip"):
                        download_url = asset["browser_download_url"]
                        break

                return {
                    "has_update": True,
                    "version": latest_version,
                    "download_url": download_url,
                    "release_notes": data.get("body", ""),
                    "error": None
                }

            return {"has_update": False, "version": latest_version, "error": None}

        except Exception as e:
            return {
                "has_update": False,
                "error": f"Failed to check updates: {str(e)}"
            }

    def backup_current_app(self) -> tuple[bool, str]:
        """
        Backup current app version before update
        Returns: (success: bool, backup_path: str)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_folder / \
                f"backup_{self.current_version}_{timestamp}"

            # Create backup
            if backup_path.exists():
                shutil.rmtree(backup_path)

            # Copy entire app folder, ignoring backup and venv/temp dirs to avoid recursion
            if self.app_folder.exists():
                ignore_patterns = shutil.ignore_patterns(
                    'app_backups', 'venv', 'update_temp', '__pycache__', 
                    '.git', 'dist', 'build', '*.old'
                )
                shutil.copytree(
                    self.app_folder, 
                    backup_path, 
                    ignore=ignore_patterns
                )

            # Also backup config
            config_backup = self.backup_folder / \
                f"config_{self.current_version}_{timestamp}.yaml"
            if os.path.exists("config.yaml"):
                shutil.copy("config.yaml", config_backup)

            return True, str(backup_path)

        except Exception as e:
            return False, f"Backup failed: {str(e)}"

    def download_update(self, download_url: str, output_file: str = "update.zip", progress_callback=None) -> tuple[bool, str]:
        """
        Download new version from GitHub
        Returns: (success: bool, file_path: str)
        """
        try:
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()

            # Download with progress
            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total)

            return True, output_file

        except Exception as e:
            return False, f"Download failed: {str(e)}"

    def extract_update(self, zip_file: str) -> tuple[bool, str]:
        """
        Extract downloaded zip to app folder
        Returns: (success: bool, message: str)
        """
        try:
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                # Extract to temp first
                temp_extract = Path("update_temp")
                if temp_extract.exists():
                    shutil.rmtree(temp_extract)

                zip_ref.extractall(temp_extract)

            # Find the extracted AutoPostingTool folder
            extracted_app = None
            # Look for sub-folder (Legacy/Standard structure)
            for item in temp_extract.iterdir():
                if item.is_dir() and "AutoPostingTool" in item.name:
                    extracted_app = item
                    break

            # If not found in sub-folder (Modern structure v1.3.25+), check if EXE exists in root
            if not extracted_app:
                # Check root extracted folder directly
                if any(item.name == "AutoPostingTool.exe" for item in temp_extract.iterdir()):
                    extracted_app = temp_extract
                else:
                    return False, f"Extracted contents not recognized as AutoPostingTool app folder"

            # Robust overwrite for Windows (handles locked files by renaming them)
            if self.app_folder.exists():
                # 1. Backup config
                config_bak = None
                config_path = Path("config.yaml")
                if config_path.exists():
                    config_bak = Path("config_temp.yaml")
                    shutil.copy(config_path, config_bak)

                # 2. Iterate through new app and copy into place
                for src_item in extracted_app.rglob('*'):
                    rel_path = src_item.relative_to(extracted_app)
                    dest_target = self.app_folder / rel_path

                    if src_item.is_dir():
                        dest_target.mkdir(parents=True, exist_ok=True)
                    else:
                        # If file exists and locked, rename first
                        if dest_target.exists():
                            try:
                                dest_target.unlink()
                            except Exception:
                                # Locked? Rename to .old
                                try:
                                    temp_old = dest_target.with_suffix(
                                        dest_target.suffix + ".old")
                                    if temp_old.exists():
                                        temp_old.unlink(missing_ok=True)
                                    os.rename(str(dest_target), str(temp_old))
                                except Exception:
                                    pass  # Give up on this specific file

                        shutil.copy2(src_item, dest_target)

                # 3. Restore config
                if config_bak and config_bak.exists():
                    shutil.copy(config_bak, config_path)
                    config_bak.unlink()

            # Cleanup
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            if os.path.exists(zip_file):
                os.unlink(zip_file)

            return True, "Update extracted successfully"

        except Exception as e:
            return False, f"Extraction failed: {str(e)}"

    def restore_from_backup(self, backup_path: str) -> tuple[bool, str]:
        """
        Restore app from backup if update fails
        Returns: (success: bool, message: str)
        """
        try:
            backup_dir = Path(backup_path)

            if not backup_dir.exists():
                return False, f"Backup not found: {backup_path}"

            # Safely restore: Don't remove the root app folder (it might contain backups)
            # Instead, remove contents EXCEPT the backup folder itself if it were inside
            for item in self.app_folder.iterdir():
                if item.is_dir():
                    # Protect backup folder if it happens to be here
                    if item.name not in ["app_backups", "_internal/app_backups", "AutoPostingTool_Backups"]:
                        shutil.rmtree(item)
                else:
                    item.unlink()

            # Restore from backup
            for src_item in backup_dir.iterdir():
                dest_target = self.app_folder / src_item.name
                if src_item.is_dir():
                    shutil.copytree(src_item, dest_target)
                else:
                    shutil.copy2(src_item, dest_target)

            return True, "App restored from backup successfully"

        except Exception as e:
            return False, f"Restore failed: {str(e)}"

    def cleanup_old_backups(self, keep_count: int = 3):
        """Keep only recent backups, cleanup old ones"""
        try:
            backups = sorted(
                [d for d in self.backup_folder.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            # Delete old backups after keeping recent ones
            for old_backup in backups[keep_count:]:
                shutil.rmtree(old_backup)

        except Exception as e:
            print(f"Cleanup failed: {e}")

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare versions: v1 > v2 returns 1, equal returns 0, v1 < v2 returns -1
        """
        try:
            v1_parts = [int(x) for x in v1.split(".")]
            v2_parts = [int(x) for x in v2.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))

            if v1_parts > v2_parts:
                return 1
            elif v1_parts < v2_parts:
                return -1
            else:
                return 0
        except Exception as e:
            log_debug(f"Version comparison error: {str(e)}")
            return 0
