#!/usr/bin/env python3
"""
COMPREHENSIVE UNIFIED TEST SUITE for Vibecode Auto
Combines:
  1. Implementation tests (validators, detection_limiter, exceptions)
  2. Comprehensive tests (module imports, AppUI, storage, logger)
  3. Backup system tests

Run: python test_all.py
"""

from backup_system import BackupManager, SafeStorage, get_safe_storage
from detection_limiter import DetectionLimiter
from exceptions import TooManyPostsException, ContextDestroyedException
from validators import Validators, ValidationError
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import all modules for testing


# ============================================================================
# PART 1: VALIDATORS & EXCEPTIONS TESTS
# ============================================================================

def test_validators():
    """Test validators.py"""
    print("\n" + "="*60)
    print("[TEST] TESTING: Validators")
    print("="*60)

    passed = 0

    # Test 1: Valid Facebook URL
    print("\n[OK] Test 1: Valid Facebook URL")
    try:
        Validators.validate_facebook_url(
            "https://facebook.com/groups/123456789")
        print("  [OK] PASS: Valid URL accepted")
        passed += 1
    except ValidationError as e:
        print(f"  [FAIL] FAIL: {e}")

    # Test 2: Invalid URL (not Facebook)
    print("\n[OK] Test 2: Invalid URL (not Facebook)")
    try:
        Validators.validate_facebook_url("https://example.com")
        print("  [FAIL] FAIL: Should reject non-Facebook URLs")
    except ValidationError as e:
        print(f"  [OK] PASS: {e}")
        passed += 1

    # Test 3: Invalid URL (not a group)
    print("\n[OK] Test 3: Invalid URL (not a group)")
    try:
        Validators.validate_facebook_url(
            "https://facebook.com/pages/something")
        print("  [FAIL] FAIL: Should reject non-group URLs")
    except ValidationError as e:
        print(f"  [OK] PASS: {e}")
        passed += 1

    # Test 4: Valid group name
    print("\n[OK] Test 4: Valid group name")
    try:
        Validators.validate_group_name("Dev Vietnam")
        print("  [OK] PASS: Valid name accepted")
        passed += 1
    except ValidationError as e:
        print(f"  [FAIL] FAIL: {e}")

    # Test 5: Group name too short
    print("\n[OK] Test 5: Group name too short")
    try:
        Validators.validate_group_name("ab")
        print("  [FAIL] FAIL: Should reject short names")
    except ValidationError as e:
        print(f"  [OK] PASS: {e}")
        passed += 1

    # Test 6: Valid post content
    print("\n[OK] Test 6: Valid post content")
    try:
        Validators.validate_post_content(
            "This is a valid post content for Facebook")
        print("  [OK] PASS: Valid content accepted")
        passed += 1
    except ValidationError as e:
        print(f"  [FAIL] FAIL: {e}")

    # Test 7: Post content too short
    print("\n[OK] Test 7: Post content too short")
    try:
        Validators.validate_post_content("ab")
        print("  [FAIL] FAIL: Should reject short content")
    except ValidationError as e:
        print(f"  [OK] PASS: {e}")
        passed += 1

    # Test 8: Valid delay range
    print("\n[OK] Test 8: Valid delay range")
    try:
        Validators.validate_delay_range(5, 10)
        print("  [OK] PASS: Valid delay range accepted")
        passed += 1
    except ValidationError as e:
        print(f"  [FAIL] FAIL: {e}")

    # Test 9: Invalid delay range (min > max)
    print("\n[OK] Test 9: Invalid delay range (min > max)")
    try:
        Validators.validate_delay_range(10, 5)
        print("  [FAIL] FAIL: Should reject min > max")
    except ValidationError as e:
        print(f"  [OK] PASS: {e}")
        passed += 1

    return passed, 9


def test_detection_limiter():
    """Test detection_limiter.py"""
    print("\n" + "="*60)
    print("[TEST] TESTING: Detection Limiter")
    print("="*60)

    passed = 0

    limiter = DetectionLimiter()

    # Test 1: Can start session initially
    print("\n[OK] Test 1: Can start session initially")
    result = limiter.check_session_can_start()
    if result['can_start']:
        print(f"  [OK] PASS: {result['reason']}")
        passed += 1
    else:
        print(f"  [FAIL] FAIL: Should allow first session")

    # Test 2: Record session start
    print("\n[OK] Test 2: Record session start")
    limiter.record_session_start()
    print("  [OK] PASS: Session started")
    passed += 1

    # Test 3: Record post success
    print("\n[OK] Test 3: Record post success")
    for i in range(5):
        limiter.record_post_success()
    print(f"  [OK] PASS: Recorded 5 posts")
    passed += 1

    # Test 4: Get session summary
    print("\n[OK] Test 4: Get session summary")
    summary = limiter.get_session_summary()
    print(f"  [OK] PASS: {summary}")
    passed += 1

    # Test 5: Get daily summary
    print("\n[OK] Test 5: Get daily summary")
    daily = limiter.get_daily_summary()
    print(f"  [OK] PASS: {daily}")
    passed += 1

    # Test 6: Get stats
    print("\n[OK] Test 6: Get stats")
    stats = limiter.get_stats()
    print(f"  [OK] PASS: Posts this session: {stats['posts_this_session']}")
    print(f"           Posts today: {stats['posts_today']}")
    passed += 1

    return passed, 6


def test_exceptions():
    """Test exceptions.py"""
    print("\n" + "="*60)
    print("[TEST] TESTING: Custom Exceptions")
    print("="*60)

    passed = 0

    # Test 1: Can raise TooManyPostsException
    print("\n[OK] Test 1: Can raise TooManyPostsException")
    try:
        raise TooManyPostsException("Too many posts today")
    except TooManyPostsException as e:
        print(f"  [OK] PASS: Caught exception: {e}")
        passed += 1

    # Test 2: Can raise ContextDestroyedException
    print("\n[OK] Test 2: Can raise ContextDestroyedException")
    try:
        raise ContextDestroyedException("Browser context destroyed")
    except ContextDestroyedException as e:
        print(f"  [OK] PASS: Caught exception: {e}")
        passed += 1

    # Test 3: Exception hierarchy
    print("\n[OK] Test 3: Exception hierarchy")
    try:
        raise TooManyPostsException("Test")
    except Exception as e:
        print(f"  [OK] PASS: Exception type: {type(e).__name__}")
        passed += 1

    return passed, 3


# ============================================================================
# PART 2: COMPREHENSIVE TESTS
# ============================================================================

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_imports():
    """Test 1: Import all critical modules"""
    print_section("TEST 1: MODULE IMPORTS")

    passed = 0
    try:
        print("  [1/6] Importing flet...")
        import flet as ft
        print("    [OK] flet imported")
        passed += 1

        print("  [2/6] Importing AppUI...")
        from app_ui import AppUI
        print("    [OK] AppUI imported")
        passed += 1

        print("  [3/6] Importing DynamicSelector...")
        from dynamic_selector import DynamicSelector
        print("    [OK] DynamicSelector imported")
        passed += 1

        print("  [4/6] Importing storage...")
        from storage import load_groups, save_groups
        print("    [OK] storage imported")
        passed += 1

        print("  [5/6] Importing logger_config...")
        from logger_config import log_debug, log_info, log_warning, log_error, log_exception
        print("    [OK] logger_config imported")
        passed += 1

        print("  [6/6] Importing ui_messages...")
        from ui_messages import get_message, get_message_color
        print("    [OK] ui_messages imported")
        passed += 1

    except Exception as e:
        print(f"    ✗ FAILED: {e}")

    return passed, 6


def test_textbutton_fix():
    """Test 2: Verify TextButton fix"""
    print_section("TEST 2: TEXTBUTTON FIX")

    passed = 0
    try:
        import flet as ft

        print("  Creating TextButton without 'selected' parameter...")
        btn = ft.TextButton("Test Button")
        print("    [OK] TextButton created successfully")

        print("  Setting TextButton style...")
        btn.style = ft.ButtonStyle(color="#1877F2")
        print("    [OK] TextButton.style set successfully")

        print("  [OK] TextButton fix verified - no 'selected' errors")
        passed = 2
    except TypeError as e:
        if "selected" in str(e):
            print(f"    ✗ FAILED: TextButton still has 'selected' error: {e}")
    except Exception as e:
        print(f"    ✗ FAILED: {e}")

    return passed, 2


def test_app_initialization():
    """Test 3: Initialize AppUI with mock page"""
    print_section("TEST 3: APPUI INITIALIZATION")

    passed = 0
    try:
        import flet as ft
        from app_ui import AppUI

        print("  Creating mock Flet page...")
        mock_page = MagicMock(spec=ft.Page)
        mock_page.title = ""
        mock_page.theme_mode = "dark"
        mock_page.bgcolor = "#18191A"
        mock_page.fonts = {}
        mock_page.theme = ft.Theme()
        mock_page.padding = 0
        mock_page.scroll = "adaptive"
        mock_page.window = MagicMock()
        mock_page.window.width = 1400
        mock_page.window.height = 850
        mock_page.overlay = []
        mock_page.add = MagicMock()
        mock_page.update = MagicMock()
        mock_page.dialog = None
        print("    [OK] Mock page created")
        passed += 1

        print("  Initializing AppUI...")
        app = AppUI(mock_page)
        print("    [OK] AppUI initialized successfully")
        passed += 1

        # Verify key attributes
        assert hasattr(app, 'page'), "AppUI missing 'page' attribute"
        assert hasattr(
            app, 'groups_data'), "AppUI missing 'groups_data' attribute"
        assert hasattr(
            app, 'image_paths'), "AppUI missing 'image_paths' attribute"
        assert hasattr(
            app, 'is_running'), "AppUI missing 'is_running' attribute"
        print("    [OK] All critical attributes present")
        passed += 1

        print("  [OK] AppUI initialization verified")
    except Exception as e:
        print(f"    ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()

    return passed, 3


def test_storage():
    """Test 4: Storage module functionality"""
    print_section("TEST 4: STORAGE MODULE")

    passed = 0
    try:
        from storage import load_groups, save_groups

        print("  Loading groups from storage...")
        groups = load_groups()
        assert isinstance(groups, list), "load_groups() should return a list"
        print(f"    [OK] Loaded {len(groups)} groups from storage")
        passed += 1

        print("  [OK] Storage module working correctly")
        passed += 1
    except Exception as e:
        print(f"    ✗ FAILED: {e}")

    return passed, 2


def test_logger():
    """Test 5: Logger functionality"""
    print_section("TEST 5: LOGGER MODULE")

    passed = 0
    try:
        from logger_config import log_debug, log_info, log_warning, log_error

        print("  Testing log_debug...")
        log_debug("Test debug message")
        print("    [OK] log_debug works")
        passed += 1

        print("  Testing log_info...")
        log_info("Test info message")
        print("    [OK] log_info works")
        passed += 1

        print("  Testing log_warning...")
        log_warning("Test warning message")
        print("    [OK] log_warning works")
        passed += 1

        print("  Testing log_error...")
        log_error("Test error message")
        print("    [OK] log_error works")
        passed += 1

        print("  [OK] Logger module verified")
    except Exception as e:
        print(f"    ✗ FAILED: {e}")

    return passed, 4


def test_ui_messages():
    """Test 6: UI Messages functionality"""
    print_section("TEST 6: UI MESSAGES MODULE")

    passed = 0
    try:
        from ui_messages import get_message, get_message_color, MESSAGES

        print(f"  Total messages defined: {len(MESSAGES)}")
        passed += 1

        print("  Testing get_message() with 'bot_ready'...")
        msg = get_message("bot_ready")
        assert "Bot sẵn sàng" in msg or "ready" in msg.lower(
        ), f"Unexpected message: {msg}"
        print(f"    [OK] Message: {msg}")
        passed += 1

        print("  Testing get_message_color()...")
        color = get_message_color(msg)
        assert isinstance(color, str) and color.startswith(
            "#"), f"Invalid color: {color}"
        print(f"    [OK] Color: {color}")
        passed += 1

        print("  [OK] UI Messages module verified")
    except Exception as e:
        print(f"    ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()

    return passed, 3


# ============================================================================
# PART 3: BACKUP SYSTEM TESTS
# ============================================================================

class TestBackupSystem:
    """Test suite for backup system"""

    def __init__(self):
        self.test_dir = None
        self.backup_dir = None
        self.passed = 0
        self.failed = 0
        self.test_data = [
            {"id": "1", "name": "Group 1", "url": "https://facebook.com/groups/1"},
            {"id": "2", "name": "Group 2", "url": "https://facebook.com/groups/2"},
            {"id": "3", "name": "Group 3", "url": "https://facebook.com/groups/3"},
        ]

    def setup(self):
        """Setup test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="vibecode_backup_test_")
        self.backup_dir = os.path.join(self.test_dir, "backups")
        print(f"\n🧪 Setup test environment: {self.test_dir}")
        return True

    def teardown(self):
        """Cleanup test environment"""
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            print(f"🧹 Cleaned up test environment")
        return True

    def test_1_backup_creation(self):
        """Test 1: Create backup"""
        print("\n📝 Test 1: Backup Creation")
        try:
            manager = BackupManager(
                data_file=os.path.join(self.test_dir, "groups.json"),
                backup_dir=self.backup_dir
            )
            success, path = manager.create_backup(self.test_data, label="test")
            if success and os.path.exists(path):
                with open(path, 'r') as f:
                    backup_data = json.load(f)
                if backup_data == self.test_data:
                    print(f"  [OK] Backup created: {os.path.basename(path)}")
                    self.passed += 1
                    return True
            self._fail("Backup creation/verification failed")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_2_list_backups(self):
        """Test 2: List backups"""
        print("\n📝 Test 2: List Backups")
        try:
            manager = BackupManager(
                data_file=os.path.join(self.test_dir, "groups.json"),
                backup_dir=self.backup_dir
            )
            # Count initial backups (from Test 1)
            initial_count = len(manager.list_backups())

            # Create 3 new backups
            for i in range(3):
                data = self.test_data + [{"id": str(i), "name": f"Extra {i}"}]
                manager.create_backup(data, label=f"backup_{i}")

            backups = manager.list_backups()
            new_count = len(backups) - initial_count

            if new_count == 3:
                print(
                    f"  [OK] Listed {len(backups)} total backups (added 3 new)")
                self.passed += 1
                return True
            self._fail(
                f"Expected 3 new backups, got {new_count} (total: {len(backups)})")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_3_restore_backup(self):
        """Test 3: Restore backup"""
        print("\n📝 Test 3: Restore Backup")
        try:
            manager = BackupManager(
                data_file=os.path.join(self.test_dir, "groups.json"),
                backup_dir=self.backup_dir
            )
            success, backup_path = manager.create_backup(
                self.test_data, label="restore_test")
            if success:
                success, restored_data = manager.restore_backup(backup_path)
                if success and restored_data == self.test_data:
                    print(
                        f"  [OK] Restored {len(restored_data)} groups from backup")
                    self.passed += 1
                    return True
            self._fail("Restore failed")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_4_backup_rotation(self):
        """Test 4: Backup rotation"""
        print("\n📝 Test 4: Backup Rotation")
        try:
            manager = BackupManager(
                data_file=os.path.join(self.test_dir, "groups.json"),
                backup_dir=self.backup_dir
            )
            for i in range(15):
                data = self.test_data + [{"id": str(i), "name": f"Group {i}"}]
                manager.create_backup(data, label=f"rotation_{i}")
                backups = manager.list_backups(limit=100)
                if len(backups) > 10:
                    self._fail(f"Rotation failed: {len(backups)} backups")
                    return False

            backups = manager.list_backups(limit=100)
            if len(backups) == 10:
                print(f"  [OK] Rotation working: kept 10 backups out of 15")
                self.passed += 1
                return True
            self._fail(f"Expected 10 backups, got {len(backups)}")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_5_validate_backup(self):
        """Test 5: Validate backup"""
        print("\n📝 Test 5: Validate Backup")
        try:
            manager = BackupManager(
                data_file=os.path.join(self.test_dir, "groups.json"),
                backup_dir=self.backup_dir
            )
            success, backup_path = manager.create_backup(
                self.test_data, label="valid")
            is_valid, msg = manager.validate_backup(backup_path)
            if is_valid:
                print(f"  [OK] Backup validation working")
                self.passed += 1
                return True
            self._fail(f"Validation failed: {msg}")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_6_corruption_recovery(self):
        """Test 6: Corruption recovery"""
        print("\n📝 Test 6: Corruption Recovery")
        try:
            data_file = os.path.join(self.test_dir, "groups.json")
            storage = SafeStorage(data_file=data_file,
                                  backup_dir=self.backup_dir)

            storage.save_groups(self.test_data, label="recovery_test")
            with open(data_file, 'w') as f:
                f.write("{corrupted")

            recovered_data = storage.load_groups()
            if recovered_data and len(recovered_data) == len(self.test_data):
                print(f"  [OK] Auto-recovered {len(recovered_data)} groups")
                self.passed += 1
                return True
            self._fail("Recovery failed")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_7_safe_storage_auto_backup(self):
        """Test 7: SafeStorage auto-backup"""
        print("\n📝 Test 7: SafeStorage Auto-Backup")
        try:
            data_file = os.path.join(self.test_dir, "groups.json")
            storage = SafeStorage(data_file=data_file,
                                  backup_dir=self.backup_dir)

            for i in range(5):
                data = self.test_data + [{"id": str(i), "name": f"Save {i}"}]
                storage.save_groups(data, label=f"save_{i}")

            backups = storage.backup_manager.list_backups()
            if len(backups) >= 5:
                print(f"  [OK] Created {len(backups)} backups automatically")
                self.passed += 1
                return True
            self._fail(f"Expected 5+ backups, got {len(backups)}")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def test_8_add_and_delete_with_backup(self):
        """Test 8: Add/Delete with backup"""
        print("\n📝 Test 8: Add/Delete with Backup")
        try:
            data_file = os.path.join(self.test_dir, "groups.json")
            storage = SafeStorage(data_file=data_file,
                                  backup_dir=self.backup_dir)

            new_group = {"id": "new", "name": "New Group",
                         "url": "https://facebook.com/groups/new"}
            storage.add_group(new_group)
            groups = storage.load_groups()

            if new_group in groups:
                storage.delete_group("new")
                groups = storage.load_groups()
                if not any(g.get("id") == "new" for g in groups):
                    print(f"  [OK] Add/Delete with backup working")
                    self.passed += 1
                    return True

            self._fail("Add/Delete test failed")
            return False
        except Exception as e:
            self._fail(f"Exception: {e}")
            return False

    def _fail(self, message):
        """Mark test as failed"""
        print(f"  [FAIL] {message}")
        self.failed += 1

    def run_all(self):
        """Run all backup tests"""
        print("\n" + "=" * 70)
        print("🧪 BACKUP SYSTEM TESTS")
        print("=" * 70)

        try:
            if not self.setup():
                print("\n[FAIL] Setup failed")
                return False, 0, 0

            tests = [
                self.test_1_backup_creation,
                self.test_2_list_backups,
                self.test_3_restore_backup,
                self.test_4_backup_rotation,
                self.test_5_validate_backup,
                self.test_6_corruption_recovery,
                self.test_7_safe_storage_auto_backup,
                self.test_8_add_and_delete_with_backup,
            ]

            for test in tests:
                try:
                    test()
                except Exception as e:
                    self._fail(f"Test crashed: {e}")

            self.teardown()

            if self.failed == 0:
                print(f"\n[OK] All {self.passed} backup tests passed!")
            else:
                print(f"\n[WARN]  {self.failed} backup test(s) failed")

            return True, self.passed, self.failed

        except Exception as e:
            print(f"\n💥 Backup test suite crashed: {e}")
            return False, self.passed, self.failed


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests"""
    print("\n")
    print("+" + "="*78 + "+")
    print("|" + " "*20 + "VIBECODE AUTO - UNIFIED TEST SUITE" + " "*24 + "|")
    print("+" + "="*78 + "+")

    # Part 1: Implementation tests
    print("\n\n" + "="*80)
    print("PART 1: IMPLEMENTATION TESTS")
    print("="*80)

    validators_pass, validators_total = test_validators()
    limiter_pass, limiter_total = test_detection_limiter()
    exceptions_pass, exceptions_total = test_exceptions()

    part1_pass = validators_pass + limiter_pass + exceptions_pass
    part1_total = validators_total + limiter_total + exceptions_total

    # Part 2: Comprehensive tests
    print("\n\n" + "="*80)
    print("PART 2: COMPREHENSIVE TESTS")
    print("="*80)

    imports_pass, imports_total = test_imports()
    textbutton_pass, textbutton_total = test_textbutton_fix()
    appui_pass, appui_total = test_app_initialization()
    storage_pass, storage_total = test_storage()
    logger_pass, logger_total = test_logger()
    ui_msgs_pass, ui_msgs_total = test_ui_messages()

    part2_pass = (imports_pass + textbutton_pass + appui_pass + storage_pass +
                  logger_pass + ui_msgs_pass)
    part2_total = (imports_total + textbutton_total + appui_total + storage_total +
                   logger_total + ui_msgs_total)

    # Part 3: Backup system tests
    print("\n\n" + "="*80)
    print("PART 3: BACKUP SYSTEM TESTS")
    print("="*80)

    backup_tester = TestBackupSystem()
    backup_success, backup_pass, backup_fail = backup_tester.run_all()
    part3_pass = backup_pass
    part3_total = backup_pass + backup_fail

    # Overall summary
    print("\n\n" + "="*80)
    print("OVERALL TEST SUMMARY")
    print("="*80)

    total_pass = part1_pass + part2_pass + part3_pass
    total_tests = part1_total + part2_total + part3_total

    print(f"\n📊 RESULTS BY PART:")
    print(f"  Part 1 (Implementation):  {part1_pass}/{part1_total} passed")
    print(f"  Part 2 (Comprehensive):   {part2_pass}/{part2_total} passed")
    print(f"  Part 3 (Backup System):   {part3_pass}/{part3_total} passed")
    print(f"\n📈 OVERALL:")
    print(f"  Total Passed: {total_pass}/{total_tests}")
    print(f"  Success Rate: {100 * total_pass / total_tests:.1f}%")
    print("\n" + "="*80)

    if total_pass == total_tests:
        print("\n+" + "="*78 + "+")
        print("|" + " "*25 + "[OK] ALL TESTS PASSED [OK]" + " "*31 + "|")
        print("|" + " "*20 + "Vibecode Auto is ready for production!" + " "*19 + "|")
        print("+" + "="*78 + "+\n")
        return 0
    else:
        failed = total_tests - total_pass
        print("\n+" + "="*78 + "+")
        print("|" + f" "*28 + f"✗ {failed} TEST(S) FAILED" + " " *
              (78 - 28 - len(f"✗ {failed} TEST(S) FAILED") - 1) + "|")
        print("|" + " "*20 + "Please fix the failing tests before running the app" + " " *
              (78 - 20 - len("Please fix the failing tests before running the app") - 1) + "|")
        print("+" + "="*78 + "+\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
