"""
Recovery Manager - Handle app crashes and resume posting
Save progress to temp file so user can resume if app crashes
Thread-safe with atomic writes and size validation
"""

import json
import os
import tempfile
from datetime import datetime
from logger_config import log_info, log_error, log_warning


class RecoveryManager:
    """Manage crash recovery and posting progress"""

    RECOVERY_FILE = "recovery_state.json"
    MAX_RECOVERY_FILE_SIZE = 1 * 1024 * 1024  # 1MB max

    def __init__(self):
        self.recovery_data = None
        self.load_recovery_state()

    def load_recovery_state(self):
        """Load recovery state from file if exists, with size validation"""
        if os.path.exists(self.RECOVERY_FILE):
            try:
                # Validate file size first
                file_size = os.path.getsize(self.RECOVERY_FILE)
                if file_size > self.MAX_RECOVERY_FILE_SIZE:
                    log_warning(
                        f"⚠️ Recovery file too large ({file_size} bytes > {self.MAX_RECOVERY_FILE_SIZE}), skipping")
                    self.recovery_data = None
                    return

                with open(self.RECOVERY_FILE, 'r', encoding='utf-8') as f:
                    self.recovery_data = json.load(f)
                log_info(
                    f"📋 Found recovery state from {self.recovery_data.get('timestamp', 'unknown')}")
            except json.JSONDecodeError as e:
                log_error(f"Recovery file corrupted: {e}")
                self.recovery_data = None
            except Exception as e:
                log_error(f"Error loading recovery state: {e}")
                self.recovery_data = None
        else:
            self.recovery_data = None

    def has_recovery_state(self):
        """Check if recovery state exists"""
        return self.recovery_data is not None

    def get_recovery_state(self):
        """Get the recovery state data"""
        return self.recovery_data

    def save_progress(self, groups_data, current_index, posted_count, failed_groups, config_data):
        """Save current posting progress to recovery file (atomic write)

        Args:
            groups_data: List of groups being posted to (full dicts with name+url)
            current_index: Current group index (0-based)
            posted_count: Number of groups successfully posted
            failed_groups: List of failed group names
            config_data: Post content and images info
        """
        try:
            # Validate data before saving
            try:
                remaining = [g.get("name", "Unknown")
                             for g in groups_data[current_index:]]
            except (TypeError, KeyError) as e:
                log_error(f"Invalid groups_data structure: {e}")
                return

            # Save full group data (name+url) for resume capability
            remaining_groups_full = []
            for g in groups_data[current_index:]:
                remaining_groups_full.append({
                    "name": g.get("name", "Unknown"),
                    "url": g.get("url", "")
                })

            # Save image paths for resume (only existing files)
            image_paths = []
            for img_path in config_data.get("images", []):
                if isinstance(img_path, str) and os.path.exists(img_path):
                    image_paths.append(os.path.abspath(img_path))

            recovery_data = {
                "timestamp": datetime.now().isoformat(),
                "groups_total": len(groups_data),
                "current_index": current_index,
                "posted_count": posted_count,
                "failed_groups": list(failed_groups),  # Ensure it's a list
                "remaining_groups": remaining,
                "remaining_groups_full": remaining_groups_full,  # Full data for resume
                # Truncate content to 5000 chars (enough for resume)
                "post_content": str(config_data.get("content", ""))[:5000],
                "post_has_images": len(image_paths) > 0,
                "image_count": len(image_paths),
                "image_paths": image_paths  # Full paths for resume
            }

            # 🔒 ATOMIC WRITE: Write to temp file then rename
            # This prevents corruption if crash happens during write
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json', dir=os.path.dirname(self.RECOVERY_FILE) or '.')
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(recovery_data, f, ensure_ascii=False, indent=2)

                # Atomic rename (on Windows, need to remove old file first)
                if os.path.exists(self.RECOVERY_FILE):
                    os.remove(self.RECOVERY_FILE)
                os.rename(temp_path, self.RECOVERY_FILE)

                log_info(
                    f"💾 Progress saved: {current_index}/{len(groups_data)} groups")
            except Exception as e:
                # Clean up temp file if rename failed
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                raise e

        except Exception as e:
            log_error(f"Error saving recovery progress: {e}")

    def clear_recovery_state(self):
        """Clear recovery state (call after successful completion or manual reset)"""
        try:
            if os.path.exists(self.RECOVERY_FILE):
                os.remove(self.RECOVERY_FILE)
                log_info("✅ Recovery state cleared")
            self.recovery_data = None
        except Exception as e:
            log_error(f"Error clearing recovery state: {e}")

    def get_remaining_groups(self):
        """Get remaining groups from recovery state (full data with name+url)

        Returns:
            List of group dicts with 'name' and 'url' keys, or empty list
        """
        if not self.recovery_data:
            return []

        groups = self.recovery_data.get("remaining_groups_full", [])
        # Validate each group has required fields
        valid_groups = []
        for g in groups:
            if isinstance(g, dict) and g.get("url"):
                valid_groups.append(g)
        return valid_groups

    def get_saved_content(self):
        """Get saved post content from recovery state

        Returns:
            str: The saved post content, or empty string
        """
        if not self.recovery_data:
            return ""
        return self.recovery_data.get("post_content", "")

    def get_saved_image_paths(self):
        """Get saved image paths from recovery state (only existing files)

        Returns:
            List of absolute image path strings that still exist on disk
        """
        if not self.recovery_data:
            return []

        paths = self.recovery_data.get("image_paths", [])
        # Only return paths that still exist
        return [p for p in paths if isinstance(p, str) and os.path.exists(p)]

    def get_summary(self):
        """Get human-readable summary of recovery state

        Returns:
            dict with 'timestamp', 'posted', 'remaining', 'total', 'has_content', 'has_images'
        """
        if not self.recovery_data:
            return None

        return {
            "timestamp": self.recovery_data.get("timestamp", "?"),
            "posted": self.recovery_data.get("posted_count", 0),
            "remaining": len(self.get_remaining_groups()),
            "total": self.recovery_data.get("groups_total", 0),
            "has_content": bool(self.get_saved_content()),
            "has_images": self.recovery_data.get("post_has_images", False),
            "image_count": self.recovery_data.get("image_count", 0),
            "failed_groups": self.recovery_data.get("failed_groups", [])
        }


# Global instance
recovery_manager = RecoveryManager()
