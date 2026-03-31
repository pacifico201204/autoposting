"""
Backup System - Protect against data loss

Features:
- Automatic backup before each write
- Backup rotation (keep last 10 backups)
- Restore from backup
- Validation & integrity check
- Version history
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


# Configuration
BACKUP_DIR = "backups"
BACKUP_RETENTION = 10  # Keep last 10 backups
DATA_FILE = "groups.json"


class BackupManager:
    """
    Manage data backups - Create, restore, validate
    """
    
    def __init__(self, data_file: str = DATA_FILE, backup_dir: str = BACKUP_DIR):
        self.data_file = data_file
        self.backup_dir = backup_dir
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            print(f"✅ Created backup directory: {self.backup_dir}")
    
    def create_backup(self, data: Any, label: str = "") -> Tuple[bool, str]:
        """
        Create a backup of data
        
        Args:
            data: Data to backup
            label: Optional label (e.g., "manual", "auto", "pre-deletion")
            
        Returns:
            (success: bool, backup_path: str)
        """
        try:
            self._ensure_backup_dir()
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            label_str = f"_{label}" if label else ""
            backup_filename = f"backup_{timestamp}{label_str}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Write backup
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # Rotate old backups
            self._rotate_backups()
            
            print(f"✅ Backup created: {backup_path}")
            return True, backup_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False, ""
    
    def restore_backup(self, backup_path: str) -> Tuple[bool, Any]:
        """
        Restore data from backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            (success: bool, data: Any)
        """
        try:
            if not os.path.exists(backup_path):
                print(f"❌ Backup not found: {backup_path}")
                return False, None
            
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"✅ Backup restored: {backup_path}")
            return True, data
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False, None
    
    def get_latest_backup(self) -> Optional[str]:
        """Get path to latest backup"""
        try:
            backup_files = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith("backup_")],
                reverse=True
            )
            if backup_files:
                return os.path.join(self.backup_dir, backup_files[0])
        except Exception as e:
            print(f"❌ Error finding backups: {e}")
        return None
    
    def list_backups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List available backups
        
        Returns:
            List of backup info dicts
        """
        try:
            backup_files = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith("backup_")],
                reverse=True
            )[:limit]
            
            backups = []
            for backup_file in backup_files:
                backup_path = os.path.join(self.backup_dir, backup_file)
                stat = os.stat(backup_path)
                backups.append({
                    "filename": backup_file,
                    "path": backup_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            
            return backups
            
        except Exception as e:
            print(f"❌ Error listing backups: {e}")
            return []
    
    def _rotate_backups(self):
        """Remove old backups, keep only last N"""
        try:
            backup_files = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith("backup_")],
                reverse=True
            )
            
            # Remove old backups
            for old_backup in backup_files[BACKUP_RETENTION:]:
                old_path = os.path.join(self.backup_dir, old_backup)
                os.remove(old_path)
                print(f"🗑️  Removed old backup: {old_backup}")
                
        except Exception as e:
            print(f"⚠️  Warning during backup rotation: {e}")
    
    def validate_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Validate backup file integrity
        
        Returns:
            (is_valid: bool, message: str)
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"❌ File not found: {backup_path}"
            
            # Try to load JSON
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check if it's a list (groups data)
            if not isinstance(data, list):
                return False, f"❌ Invalid backup format (expected list, got {type(data).__name__})"
            
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            return True, f"✅ Valid backup ({len(data)} groups, {size_mb:.2f} MB)"
            
        except json.JSONDecodeError as e:
            return False, f"❌ Invalid JSON: {e}"
        except Exception as e:
            return False, f"❌ Validation error: {e}"


class SafeStorage:
    """
    Safe storage wrapper - Always create backup before write
    """
    
    def __init__(self, data_file: str = DATA_FILE, backup_dir: str = BACKUP_DIR):
        self.data_file = data_file
        self.backup_manager = BackupManager(data_file, backup_dir)
    
    def load_groups(self) -> List[Dict[str, Any]]:
        """
        Load groups from file, recover from backup if corrupted
        
        Returns:
            List of groups
        """
        # Try main file first
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    print(f"✅ Loaded {len(data)} groups from {self.data_file}")
                    return data
            except json.JSONDecodeError as e:
                print(f"⚠️  Main file corrupted: {e}")
        
        # Try to recover from latest backup
        latest_backup = self.backup_manager.get_latest_backup()
        if latest_backup:
            success, data = self.backup_manager.restore_backup(latest_backup)
            if success:
                print(f"⚠️  Recovered from backup: {latest_backup}")
                return data
        
        # No recovery possible
        print("⚠️  No data found, returning empty list")
        return []
    
    def save_groups(self, data: List[Dict[str, Any]], label: str = "auto") -> bool:
        """
        Save groups with automatic backup
        
        Args:
            data: Groups to save
            label: Backup label (e.g., "auto", "manual", "pre-deletion")
            
        Returns:
            Success status
        """
        try:
            # Create backup BEFORE write
            success, backup_path = self.backup_manager.create_backup(data, label=label)
            if not success:
                print("⚠️  Backup failed, but continuing with write...")
            
            # Write main file
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            print(f"✅ Saved {len(data)} groups to {self.data_file}")
            return True
            
        except Exception as e:
            print(f"❌ Save failed: {e}")
            print(f"⚠️  Data may be lost! Latest backup: {self.backup_manager.get_latest_backup()}")
            return False
    
    def add_group(self, group_data: Dict[str, Any]) -> bool:
        """
        Add new group with backup
        
        Args:
            group_data: Group to add
            
        Returns:
            Success status
        """
        try:
            groups = self.load_groups()
            groups.append(group_data)
            return self.save_groups(groups, label="add_group")
        except Exception as e:
            print(f"❌ Add group failed: {e}")
            return False
    
    def delete_group(self, group_id: str) -> bool:
        """
        Delete group with backup (before deletion)
        
        Args:
            group_id: ID of group to delete
            
        Returns:
            Success status
        """
        try:
            groups = self.load_groups()
            
            # Backup BEFORE deletion
            self.backup_manager.create_backup(groups, label="pre_deletion")
            
            # Remove group
            groups = [g for g in groups if g.get("id") != group_id]
            
            return self.save_groups(groups, label="delete_group")
        except Exception as e:
            print(f"❌ Delete group failed: {e}")
            return False


# Global instance
_safe_storage = None


def get_safe_storage() -> SafeStorage:
    """Get global SafeStorage instance"""
    global _safe_storage
    if _safe_storage is None:
        _safe_storage = SafeStorage()
    return _safe_storage


# Convenience functions (backward compatible)
def load_groups() -> List[Dict[str, Any]]:
    """Load groups (backward compatible)"""
    return get_safe_storage().load_groups()


def save_groups(data: List[Dict[str, Any]]) -> bool:
    """Save groups (backward compatible)"""
    return get_safe_storage().save_groups(data)


# ============================================================================
# BACKUP UTILITIES
# ============================================================================

def get_backup_manager() -> BackupManager:
    """Get backup manager instance"""
    return get_safe_storage().backup_manager


def list_backups() -> List[Dict[str, Any]]:
    """List available backups"""
    return get_backup_manager().list_backups()


def restore_from_backup(backup_path: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Restore groups from backup file
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        (success: bool, groups: list)
    """
    success, data = get_backup_manager().restore_backup(backup_path)
    return success, data if data else []


def validate_backup_file(backup_path: str) -> Tuple[bool, str]:
    """
    Validate backup file
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        (is_valid: bool, message: str)
    """
    return get_backup_manager().validate_backup(backup_path)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: Safe storage with auto backup
----
from backup_system import get_safe_storage

storage = get_safe_storage()

# Load groups (with recovery from backup if corrupted)
groups = storage.load_groups()

# Save groups (creates backup automatically)
storage.save_groups(groups)

# Add group (with backup)
storage.add_group({"id": "123", "name": "Test"})

# Delete group (backup before deletion)
storage.delete_group("123")


EXAMPLE 2: List and restore backups
----
from backup_system import list_backups, restore_from_backup

# List available backups
backups = list_backups()
for backup in backups:
    print(f"  {backup['filename']} ({backup['size']} bytes)")

# Restore from specific backup
success, groups = restore_from_backup(backups[0]['path'])


EXAMPLE 3: Manual backup
----
from backup_system import get_backup_manager

manager = get_backup_manager()

# Create manual backup
success, path = manager.create_backup(my_data, label="manual")

# Validate backup
is_valid, message = manager.validate_backup(path)
print(message)

# Get latest backup
latest = manager.get_latest_backup()
"""
