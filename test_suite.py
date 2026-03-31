import unittest
import os
import sys
import tempfile
import json
import logging
from unittest.mock import patch, MagicMock

# ==============================================================================
# IMPORT APPLICATION MODULES
# ==============================================================================
# Thêm đường dẫn thư mục hiện tại vào sys.path để import
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils import get_resource_path
from validators import Validators, ValidationError
from exceptions import TooManyPostsException, ContextDestroyedException
from detection_limiter import DetectionLimiter
from thread_safety import ThreadSafeAutoRunner, DataModificationGuard, get_auto_runner
from recovery_manager import RecoveryManager
from backup_system import BackupManager, SafeStorage
from posting_engine import PostingEngine


# Tắt logs in ra console trong lúc test để output sạch sẽ hơn
logging.getLogger("autoposting_app").setLevel(logging.CRITICAL)

# ==============================================================================
# TEST SUITE 1: TIỆN ÍCH & RÀ SOÁT ĐỊNH DẠNG (UTILITIES & VALIDATORS)
# ==============================================================================
class TestUtilitiesAndValidators(unittest.TestCase):
    def test_get_resource_path(self):
        """Kiểm tra hàm get_resource_path trả về đúng định dạng thư mục"""
        path = get_resource_path("config.yaml")
        self.assertTrue(path.endswith("config.yaml"))
        self.assertTrue(os.path.isabs(path))

    def test_facebook_url_validation(self):
        """Rà soát logic kiểm tra URL Facebook Group"""
        # Hợp lệ (nếu k ném lỗi là PASS)
        Validators.validate_facebook_url("https://facebook.com/groups/123")
        Validators.validate_facebook_url("https://www.facebook.com/groups/abc/")
        Validators.validate_facebook_url("https://m.facebook.com/groups/group.name")
        
        # Không hợp lệ (cần ném lỗi ValidationError)
        with self.assertRaises(ValidationError):
            Validators.validate_facebook_url("https://facebook.com/pages/123")
        with self.assertRaises(ValidationError):
            Validators.validate_facebook_url("https://google.com/groups/123")
        with self.assertRaises(ValidationError):
            Validators.validate_facebook_url("not a url")

    def test_post_content_length(self):
        """Rà soát ràng buộc chiều dài nội dung bài viết"""
        # Hợp lệ
        Validators.validate_post_content("Nội dung ngắn hợp lý đủ 10 ký tự")
        
        # Quá ngắn hoặc trống
        with self.assertRaises(ValidationError):
            Validators.validate_post_content("ab")
        with self.assertRaises(ValidationError):
            Validators.validate_post_content("")

    def test_delay_margins(self):
        """Rà soát cài đặt delay trước khi đăng bài"""
        Validators.validate_delay_range(5, 10)
        
        # Phải ném lỗi do min > max
        with self.assertRaises(ValidationError):
            Validators.validate_delay_range(15, 10)


# ==============================================================================
# TEST SUITE 2: LUỒNG AN TOÀN & GIỚI HẠN (SAFETY & LIMITS)
# ==============================================================================
class TestSafetySystems(unittest.TestCase):
    def setUp(self):
        # Đảm bảo runner sạch trước mỗi test
        global _auto_runner
        from thread_safety import _auto_runner
        if _auto_runner:
            _auto_runner.mark_finished()

    def test_thread_safety(self):
        """Phát hiện lỗi Race Condition & Chặn thao tác cấm khi đang tự động đăng"""
        runner = ThreadSafeAutoRunner()
        self.assertFalse(runner.is_running())
        self.assertTrue(runner.can_start())
        self.assertTrue(runner.is_running())
        
        # Bắt đầu chạy lại khi đang chạy sẽ bị từ chối
        self.assertFalse(runner.can_start())
        
        runner.mark_finished()
        self.assertFalse(runner.is_running())

    def test_data_modification_guard(self):
        """Kiểm tra ngăn user sửa thông tin trong khi post"""
        guard = DataModificationGuard()
        self.assertTrue(guard.can_modify())
        
        guard.set_automation_running(True)
        self.assertFalse(guard.can_modify())
        with self.assertRaises(RuntimeError):
            guard.must_be_idle("Xóa Nhóm")
            
        guard.set_automation_running(False)
        self.assertTrue(guard.can_modify())

    def test_detection_limiter(self):
        """Đảm bảo Limit dừng thuật toán nếu đăng quá số lượng Facebook cho phép"""
        limiter = DetectionLimiter()
        limiter.MAX_POSTS_PER_SESSION = 2
        limiter.posts_today = 0
        limiter.posts_this_session = 0
        
        # Cho phép post bài đầu và thứ 2
        req_1 = limiter.check_can_post_in_group("Test")
        self.assertTrue(req_1['can_post'])
        limiter.record_post_success()
        limiter.record_post_success()
        
        # Vượt quá giới hạn session limit
        req_final = limiter.check_can_post_in_group("Test")
        self.assertFalse(req_final['can_post'])
        self.assertIn("giới hạn 2 bài", req_final['reason'])


# ==============================================================================
# TEST SUITE 3: KHÔI PHỤC & SAO LƯU (RECOVERY & BACKUPS)
# ==============================================================================
class TestRecoveryAndBackup(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_file = os.path.join(self.temp_dir.name, "app_data.json")
        self.backup_dir = os.path.join(self.temp_dir.name, "backups")
        
        # Fake recovery json location
        self.recovery_patcher = patch('recovery_manager.RecoveryManager.RECOVERY_FILE', 
                                      os.path.join(self.temp_dir.name, "recovery_state.json"))
        self.recovery_patcher.start()
        
    def tearDown(self):
        self.recovery_patcher.stop()
        self.temp_dir.cleanup()

    def test_backup_and_restore(self):
        """Rà soát lỗi mất dữ liệu qua module Backup Manager (Group List)"""
        manager = BackupManager(data_file=self.storage_file, backup_dir=self.backup_dir)
        test_data = [{"id": "1", "name": "Vibecode Devs"}, {"id": "2", "name": "FB Marketing"}]
        
        # Tạo file backup
        success, backup_path = manager.create_backup(test_data, label="test_backup")
        self.assertTrue(success)
        self.assertTrue(os.path.exists(backup_path))
        
        # Khôi phục file backup
        restore_success, restored_data = manager.restore_backup(backup_path)
        self.assertTrue(restore_success)
        self.assertEqual(restored_data, test_data)

    def test_recovery_manager_saves_full_urls(self):
        """Tái hiện crash và đảm bảo State lưu đủ Full List Groups & Ảnh (không bị mất URL)"""
        rm = RecoveryManager()
        groups_data = [
            {"name": "Python VN", "url": "https://fb.com/A"},
            {"name": "Marketing VN", "url": "https://fb.com/B"}
        ]
        
        # Giả lập đang xử lý ở index 0 thì bị văng
        rm.save_progress(
            groups_data=groups_data,
            current_index=0,
            posted_count=0,
            failed_groups=[],
            config_data={"content": "Xin chào!", "images": []}
        )
        
        # Ứng dụng khởi động lại và load State
        rm.load_recovery_state()
        self.assertTrue(rm.has_recovery_state())
        
        remaining = rm.get_remaining_groups()
        self.assertEqual(len(remaining), 2)
        # Bắt buộc phải lưu cả name và URL 
        self.assertEqual(remaining[1]['url'], "https://fb.com/B")
        self.assertEqual(rm.get_saved_content(), "Xin chào!")
        
        rm.clear_recovery_state()


# ==============================================================================
# TEST SUITE 4: POSTING ENGINE & COMPONENT INTEGRATION
# ==============================================================================
class TestIntegrations(unittest.TestCase):
    def test_posting_engine_loose_coupling(self):
        """Đảm bảo PostingEngine không bị kẹt vì giao diện UI bằng Mock Obj"""
        mock_ui = MagicMock()
        mock_ui.config = {}
        mock_ui.colors = {"text_muted": "#555"}
        
        try:
            engine = PostingEngine(mock_ui)
            # Thử gọi Log thông qua Engine sẽ truyền vào AppUI (Loose Coupling)
            engine.log_msg("Đang chạy auto...", color="#555", is_technical=False)
            mock_ui.log_msg.assert_called_with("Đang chạy auto...", color="#555", is_technical=False)
        except Exception as e:
            self.fail(f"PostingEngine lỗi khởi tạo: {e}")


if __name__ == '__main__':
    print("*" * 80)
    print("BẮT ĐẦU CHẠY KIỂM THỬ TOÀN DIỆN (COMPREHENSIVE ERROR SCAN) MỚI")
    print("*" * 80)
    unittest.main(verbosity=2)
