"""
Posting Engine Module - Core Facebook auto-posting automation
Extracted from app_ui_main.py for better separation of concerns.

Responsibilities:
- Launch and manage Playwright browser
- Navigate to Facebook groups
- Type content with human-like behavior
- Upload images
- Submit posts
- Handle errors and retries
"""

import os
import sys
import random
import asyncio
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from exceptions import TooManyPostsException, ContextDestroyedException
from detection_limiter import DetectionLimiter
from validators import Validators, ValidationError
from dynamic_selector import DynamicSelector
from logger_config import log_debug, log_info, log_warning, log_error, log_exception
from recovery_manager import recovery_manager
from retry_logic import retry_async
from thread_safety import get_auto_runner, get_modification_guard
auto_runner = get_auto_runner()
mod_guard = get_modification_guard()


from utils import get_resource_path, get_writable_path


class PostingEngine:
    """
    Core Facebook auto-posting engine.

    Handles all browser automation logic separated from the UI layer.
    Communicates back to UI via callbacks (log_callback, snack_callback, etc.)
    """

    def __init__(self, app_ui):
        """
        Initialize PostingEngine with reference to AppUI for callbacks and state.

        Args:
            app_ui: Reference to the AppUI instance for accessing:
                - auto_runner.is_running() (thread-safe state check)
                - app_ui.text_content.value (read)
                - app_ui.image_paths (read)
                - app_ui.post_delay_min / post_delay_max (read)
                - app_ui.log_msg() (callback)
                - app_ui.show_snack() (callback)
                - app_ui.add_to_history() (callback)
                - app_ui.history_list_view (read)
                - app_ui.clear_all_images() (callback)
                - app_ui.detection_limiter (read)
                - app_ui.page (read - for page.update())
        """
        self.app = app_ui
        self.pw_instance = None
        self.pw_context = None

    def log_msg(self, msg, color=None, is_technical=False):
        """Proxy to AppUI log_msg"""
        if color is None:
            from app_ui.ui_builder import COLORS
            color = COLORS["text_muted"]
        self.app.log_msg(msg, color=color, is_technical=is_technical)

    def _get_colors(self):
        """Get COLORS dict from app_ui"""
        from app_ui.ui_builder import COLORS
        return COLORS

    def _get_config(self):
        """Get CONFIG from app_ui"""
        return self.app.config

    async def run_facebook_auto(self, selected_groups):
        """
        Main automation loop - posts content to selected Facebook groups.
        """
        self.log_msg(f"Automation thread started for {len(selected_groups)} groups.", is_technical=True)
        COLORS = self._get_colors()
        CONFIG = self._get_config()

        playwright_instance = self.pw_instance
        browser_context = self.pw_context
        page_pw = None  # Will be set after browser launch

        # Track job for history
        job_id = len(self.app.history_list_view.controls) + 1
        current_time = datetime.now().strftime("%H:%M:%S")
        post_content = self.app.text_content.value.strip()
        thumb_img = self.app.image_paths[0] if self.app.image_paths else None
        target_group_names = [g.get("name", "Unknown") for g in selected_groups]

        job_data = {
            "id": job_id,
            "time": current_time,
            "content": post_content if post_content else "(Chỉ đăng ảnh)",
            "thumbnail": thumb_img,
            "groups": target_group_names,
            "status": "Running"
        }
        self.app.add_to_history(job_data)
        final_status = "Success"

        # Helper function for resilient actions with retries
        async def safe_action(action_func, log_prefix="Hành động"):
            for retry in range(3):
                if not auto_runner.is_running():
                    return False

                # Check if page is still valid before each retry
                try:
                    if page_pw.is_closed():
                        self.log_msg(
                            f"{log_prefix}: Page đã đóng, không thể tiếp tục.",
                            color=COLORS["error"], is_technical=True)
                        return False
                except Exception:
                    pass

                try:
                    await action_func()
                    self.log_msg(
                        f"{log_prefix} thành công!",
                        color=COLORS["success"], is_technical=True)
                    return True
                except Exception as e:
                    error_str = str(e)
                    if "context" in error_str.lower() and "destroyed" in error_str.lower():
                        self.log_msg(
                            f"{log_prefix}: Lỗi context bị destroy: {error_str[:50]}...",
                            color=COLORS["error"], is_technical=True)
                        return False
                    else:
                        self.log_msg(
                            f"Lỗi {log_prefix} (Thử lại {retry+1}/3): {error_str[:50]}...",
                            color=COLORS["error"], is_technical=True)

                    if retry < 2:
                        await asyncio.sleep(2)
            return False

        try:
            self.log_msg("🚀 Bot đã sẵn sàng chiến đấu!",
                         color=COLORS["accent"], is_technical=True)

            # === LAUNCH BROWSER ===
            if browser_context is None or playwright_instance is None:
                self.log_msg("Đang mở trình duyệt...",
                             color=COLORS["accent"], is_technical=True)
                playwright_instance = await async_playwright().start()
                self.pw_instance = playwright_instance

                user_data_dir = get_writable_path("fb_user_data_edge")
                if not os.path.exists(user_data_dir):
                    os.makedirs(user_data_dir)

                self.log_msg(f"Launching Edge with data dir: {user_data_dir}", 
                            color=COLORS["text_muted"], is_technical=True)
                
                try:
                    browser_context = await playwright_instance.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=False,
                        channel="msedge",
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    self.pw_context = browser_context
                    self.log_msg("✓ Microsoft Edge launched.", 
                                color=COLORS["success"], is_technical=True)
                except Exception as launch_err:
                    self.log_msg(f"⚠️ Edge launch failed: {str(launch_err)[:50]}", 
                                color=COLORS["warning"], is_technical=True)
                    self.log_msg("Attempting fallback to default Chromium...", 
                                is_technical=True)
                    browser_context = await playwright_instance.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=False,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    self.pw_context = browser_context
                    self.log_msg("✓ Fallback Chromium launched.", 
                                color=COLORS["success"], is_technical=True)

            # Get existing page or create a new one
            pages = browser_context.pages
            page_pw = pages[0] if pages else await browser_context.new_page()

            # Apply Playwright Stealth
            try:
                stealth = Stealth()
                await stealth.apply_stealth_async(page_pw)
            except Exception as e:
                print(f"Stealth error: {e}")

            await asyncio.sleep(2)

            # === NAVIGATE TO FACEBOOK ===
            try:
                await page_pw.goto("https://www.facebook.com/")
            except Exception as e:
                self.log_msg(
                    f"Lỗi khi truy cập Facebook: {str(e)[:50]}",
                    color=COLORS["error"], is_technical=True)
                if not auto_runner.is_running():
                    return

            try:
                await page_pw.wait_for_selector('div[role="main"]', timeout=30000)
            except Exception as e:
                self.log_msg(
                    f"⚠️ Timeout waiting for main div: {str(e)[:50]}",
                    is_technical=True)

            # Auto-accept dialog events (leave page warnings)
            try:
                page_pw.on(
                    "dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            except Exception as e:
                self.log_msg(
                    f"Lỗi đăng ký dialog handler: {str(e)[:50]}",
                    is_technical=True)

            # === WAIT FOR LOGIN IF NEEDED ===
            await self._wait_for_login(page_pw, COLORS)

            # Stabilize after login
            timestamp = datetime.now().strftime("%H:%M")
            self.log_msg(
                f"[{timestamp}] Đang ổn định hệ thống. Nghỉ 5s trước khi tương tác...",
                color=COLORS["text_muted"], is_technical=True)
            await asyncio.sleep(5)

            # Recovery state is now handled by AppUI on startup (dialog prompt).
            # Clear any stale recovery state before starting a new session.
            if recovery_manager.has_recovery_state():
                self.log_msg(
                    "⚠️ Clearing stale recovery state from previous session",
                    color="#FF9800", is_technical=True)
                recovery_manager.clear_recovery_state()

            # === MAIN POSTING LOOP ===
            posted_count = 0
            failed_groups = []

            for i, group in enumerate(selected_groups, start=1):
                if not auto_runner.is_running():
                    self.log_msg("ĐÃ DỪNG AUTO BỞI NGƯỜI DÙNG.")
                    final_status = "Failed"
                    break

                group_url = group.get("url")
                group_name = group.get("name")
                timestamp = datetime.now().strftime("%H:%M")
                
                # Update progress bar in UI
                try:
                    self.app.update_posting_progress(i, len(selected_groups), group_name)
                except Exception as e:
                    pass

                self.log_msg(
                    f"[{timestamp}] #{i}/{len(selected_groups)} - Đang di chuyển tới Group: {group_name}...",
                    is_technical=True)

                # Save progress for crash recovery
                recovery_manager.save_progress(
                    selected_groups,
                    i - 1,
                    posted_count,
                    failed_groups,
                    {"content": self.app.text_content.value.strip(),
                     "images": self.app.image_paths}
                )

                # Validate Facebook URL
                try:
                    validation_result = Validators.validate_facebook_url_enhanced(group_url)
                    log_info(f"✓ {validation_result['message']}")
                except ValidationError as e:
                    self.log_msg(
                        f"❌ Invalid URL for '{group_name}': {str(e)}",
                        color=COLORS["error"])
                    failed_groups.append(group_name)
                    continue

                # Load content at start of each group
                content = self.app.text_content.value.strip()
                self.log_msg(
                    f"📊 Images available: {len(self.app.image_paths)} | Content: {len(content)} chars",
                    color=COLORS["text_muted"], is_technical=True)

                try:
                    # === NAVIGATE TO GROUP ===
                    try:
                        await page_pw.goto(group_url, wait_until="domcontentloaded", timeout=60000)
                        self.log_msg("✓ Đã load URL nhóm thành công", is_technical=True)
                    except Exception as e:
                        self.log_msg(
                            f"⚠️ Lỗi goto (context may be destroyed): {str(e)[:50]}",
                            is_technical=True)
                        failed_groups.append(group_name)
                        await asyncio.sleep(2)
                        continue

                    try:
                        await page_pw.wait_for_selector('div[role="main"]', timeout=30000)
                        self.log_msg("✓ Trang chính đã load", is_technical=True)
                    except Exception as e:
                        self.log_msg(
                            f"⚠️ Wait timeout main div: {str(e)[:50]}",
                            is_technical=True)

                    # Extra wait for page to be fully interactive
                    self.log_msg("⏳ Ổn định trang (chờ 4s)...",
                                 color=COLORS["text_muted"], is_technical=True)
                    await asyncio.sleep(4)

                    # Check page state
                    try:
                        page_title = await page_pw.title()
                        self.log_msg(
                            f"📄 Page title: {page_title[:40]}...",
                            is_technical=True)
                    except Exception:
                        pass

                    if i > 1:
                        self.log_msg(
                            f"🔄 Refresh page state for Group {i}...",
                            color=COLORS["text_muted"], is_technical=True)
                        try:
                            await page_pw.keyboard.press("Home")
                            await asyncio.sleep(1)
                        except Exception:
                            pass

                    if not auto_runner.is_running():
                        break

                    # === 1. CLICK POST INPUT BOX ===
                    async def click_box():
                        log_info(f"Tìm post input box trong nhóm: {group_name}")
                        selector = DynamicSelector(page_pw)
                        post_input = await selector.find_post_input_box()

                        if post_input is None:
                            log_error(f"Không tìm thấy post input box trong nhóm {group_name}")
                            raise Exception("Post input box không tìm thấy")

                        await post_input.click()
                        log_info("✓ Đã click post input box thành công")

                    box_clicked = await safe_action(click_box, log_prefix="Click ô nhập bài")

                    if not box_clicked:
                        self.log_msg(
                            f"⚠️ Nhóm này khó nhằn quá, tôi sẽ thử lại ở nhóm sau! (Không thấy ô đăng bài)",
                            color=COLORS["error"])
                        continue

                    await asyncio.sleep(3)
                    if not auto_runner.is_running():
                        break

                    # === 2. TYPE CONTENT (if any) ===
                    has_content = bool(content.strip()) if content else False
                    has_images = len(self.app.image_paths) > 0

                    if has_content:
                        async def fill_text():
                            try:
                                self.log_msg("Bắt đầu gõ nội dung (mù)...", is_technical=True)
                                for char in content:
                                    # Simulate typo (5% chance with alpha chars)
                                    if random.random() < 0.05 and char.isalpha():
                                        wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                                        try:
                                            await page_pw.keyboard.type(wrong_char)
                                        except Exception:
                                            raise Exception("Context destroyed during typing")
                                        await asyncio.sleep(random.uniform(0.1, 0.4))
                                        try:
                                            await page_pw.keyboard.press("Backspace")
                                        except Exception:
                                            raise Exception("Context destroyed during typing")
                                        await asyncio.sleep(random.uniform(0.1, 0.3))

                                    # Type correct character
                                    try:
                                        await page_pw.keyboard.type(char)
                                    except Exception:
                                        raise Exception("Context destroyed during typing")
                                    await asyncio.sleep(random.uniform(0.03, 0.15))

                                    # Simulate thinking pause (3% chance)
                                    if random.random() < 0.03:
                                        await asyncio.sleep(random.uniform(1.0, 3.0))
                            except Exception as e:
                                if "context" in str(e).lower():
                                    raise Exception("Context destroyed during typing")
                                raise

                        await safe_action(fill_text, log_prefix="Điền nội dung")
                        await asyncio.sleep(2)

                    if not auto_runner.is_running():
                        break

                    # === 3. UPLOAD IMAGES (if any) ===
                    if has_images:
                        async def upload_imgs():
                            log_info(f"Bắt đầu upload {len(self.app.image_paths)} ảnh")
                            abs_image_paths = [os.path.abspath(p) for p in self.app.image_paths]

                            self.log_msg("Đang lướt tìm ảnh...",
                                         color=COLORS["text_muted"], is_technical=True)
                            await asyncio.sleep(random.uniform(3.0, 6.0))

                            selector = DynamicSelector(page_pw)
                            input_file = await selector.find_file_input()

                            if input_file is None:
                                log_error(
                                    f"❌ LỖI: Không tìm thấy file input element trong nhóm {group_name}")
                                self.log_msg(
                                    f"⚠️ Chi tiết: Đã tìm file input nhưng không thấy",
                                    color=COLORS["error"], is_technical=True)
                                raise Exception("File input không tìm thấy")

                            self.log_msg(
                                f"📸 Uploading {len(abs_image_paths)} ảnh vào Facebook...",
                                color=COLORS["accent"], is_technical=True)

                            await input_file.set_input_files(abs_image_paths)
                            log_info(f"✓ Đã upload {len(abs_image_paths)} ảnh thành công")
                            self.log_msg(
                                f"✅ Upload image thành công: {len(abs_image_paths)} ảnh",
                                color=COLORS["success"], is_technical=True)

                            self.log_msg("Đợi Facebook xử lý ảnh...",
                                         color=COLORS["text_muted"], is_technical=True)
                            await asyncio.sleep(random.uniform(2.0, 4.0))

                        success = await safe_action(upload_imgs, log_prefix="Mở và đính kèm Upload")
                        if success:
                            timestamp_img = datetime.now().strftime("%H:%M")
                            self.log_msg(
                                f"[{timestamp_img}] Đang chờ ảnh tải lên hệ thống...",
                                is_technical=True)
                            await asyncio.sleep(5)
                        else:
                            # Upload failed - skip this group
                            self.log_msg(
                                f"❌ Nhóm {group_name}: Lỗi upload ảnh - bỏ qua nhóm này",
                                color=COLORS["error"])
                            continue

                    if not auto_runner.is_running():
                        break
                    await asyncio.sleep(3)

                    # === 3.5 CONTENT VALIDATION ===
                    # Post exactly what user provided: text-only, images-only, or both
                    if not has_content and not has_images:
                        # This should not happen (validated before start_auto),
                        # but handle defensively
                        log_warning(
                            f"Group {group_name}: Skipped - no content and no images")
                        self.log_msg(
                            f"⚠️ Nhóm {group_name}: Bỏ qua - không có nội dung và không có ảnh!",
                            color=COLORS["error"])
                        continue

                    # Log what will be posted
                    if has_content and has_images:
                        log_info(
                            f"Group {group_name}: Post validated - text ({len(content)} chars) + {len(self.app.image_paths)} images")
                        self.log_msg(
                            f"✓ Nhóm {group_name}: Sẽ đăng text ({len(content)} ký tự) + {len(self.app.image_paths)} ảnh",
                            color=COLORS["success"])
                    elif has_content:
                        log_info(
                            f"Group {group_name}: Post validated - text only ({len(content)} chars)")
                        self.log_msg(
                            f"✓ Nhóm {group_name}: Sẽ đăng text ({len(content)} ký tự)",
                            color=COLORS["success"])
                    elif has_images:
                        log_info(
                            f"Group {group_name}: Post validated - images only ({len(self.app.image_paths)} images)")
                        self.log_msg(
                            f"✓ Nhóm {group_name}: Sẽ đăng {len(self.app.image_paths)} ảnh",
                            color=COLORS["success"])

                    # === 4. SUBMIT POST ===
                    is_dry_run = CONFIG.get("app", {}).get("dry_run", False)

                    if is_dry_run:
                        # DRY RUN MODE
                        parts = []
                        if has_images:
                            parts.append(f"{len(self.app.image_paths)} ảnh")
                        if has_content:
                            parts.append(f"{len(content)} ký tự")
                        self.log_msg(
                            f"🧪 DRY RUN: Mô phỏng đăng {' + '.join(parts)}",
                            color="#FFA500")
                        log_info(
                            f"DRY RUN MODE: Group {group_name} - would post {' + '.join(parts)}")
                        submit_clicked = True
                    else:
                        async def click_post():
                            try:
                                log_info(f"Tìm và click post button trong nhóm {group_name}")

                                # Try keyboard shortcut first
                                self.log_msg(
                                    "Đang thử đăng bài bằng phím tắt (Control+Enter)...",
                                    is_technical=True)
                                try:
                                    await page_pw.keyboard.press("Control+Enter")
                                except Exception:
                                    self.log_msg(
                                        "Phím tắt không work, sẽ thử click nút",
                                        is_technical=True)
                                await asyncio.sleep(2)

                                # Use dynamic selector to find Post button
                                selector = DynamicSelector(page_pw)
                                post_button = await selector.find_post_button()

                                if post_button is not None:
                                    self.log_msg("Thử click nút Đăng...", is_technical=True)
                                    try:
                                        await post_button.click(timeout=5000)
                                    except Exception as e:
                                        if "context" in str(e).lower():
                                            raise Exception("Context destroyed during post click")
                                        raise
                                    log_info("✓ Đã click post button thành công")
                                else:
                                    log_warning(
                                        "Không tìm thấy post button, có thể phím tắt đã work")
                            except Exception as e:
                                if "context" in str(e).lower():
                                    raise
                                raise

                        submit_clicked = await safe_action(click_post, log_prefix="Click Đăng Bài")

                    # Handle failed submission
                    if not submit_clicked:
                        self.log_msg(
                            "❌ Không thể click nút Đăng. Cần kiểm tra lại giao diện Facebook.",
                            color=COLORS["error"], is_technical=True)
                        self.log_msg(
                            f"⚠️ Nhóm này khó nhằn quá, tôi sẽ thử lại ở nhóm sau!",
                            color=COLORS["error"])
                        failed_groups.append(group_name)

                        # Take error screenshot
                        err_dir = get_writable_path("error_screenshots")
                        if not os.path.exists(err_dir):
                            os.makedirs(err_dir)
                        try:
                            await page_pw.screenshot(
                                path=os.path.join(
                                    err_dir,
                                    f"error_{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                ))
                        except Exception as screenshot_err:
                            self.log_msg(
                                f"Không thể chụp screenshot: {str(screenshot_err)[:50]}",
                                is_technical=True)
                        continue

                    # === POST SUCCESS ===
                    self.log_msg("✅ Đã đăng bài thành công!", is_technical=True)
                    posted_count += 1

                    # Wait for post dialog to disappear
                    await asyncio.sleep(8)
                    self.log_msg(
                        f"Hoàn thành nhóm {i}/{len(selected_groups)}. ✅ ({posted_count} posted, {len(failed_groups)} failed)",
                        color=COLORS["success"])

                    # Cleanup: Press Escape to close any remaining popups
                    try:
                        await page_pw.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                        await page_pw.keyboard.press("Escape")
                        await asyncio.sleep(1)
                    except Exception as e:
                        self.log_msg(
                            f"Cleanup lỗi (context có thể bị destroy): {str(e)[:50]}",
                            is_technical=True)

                except Exception as group_err:
                    error_str = str(group_err)
                    if "context" in error_str.lower() and "destroyed" in error_str.lower():
                        self.log_msg(
                            f"⚠️ Nhóm {group_name}: Context bị destroy (có thể do navigation)",
                            color=COLORS["error"])
                    else:
                        self.log_msg(
                            f"⚠️ Lỗi xử lý nhóm {group_name}: {error_str[:50]}...",
                            color=COLORS["error"])
                    failed_groups.append(group_name)

                # Delay between groups (not after the last one)
                if i < len(selected_groups):
                    delay = random.randint(
                        self.app.post_delay_min, self.app.post_delay_max)
                    self.log_msg(
                        f"⏳ Chờ {delay}s trước nhóm tiếp theo",
                        color=COLORS["text_muted"])
                    await asyncio.sleep(delay)

            # === ALL GROUPS DONE ===
            summary = f"✓ HOÀN THÀNH! Posted: {posted_count}/{len(selected_groups)} | Failed: {len(failed_groups)}"
            if failed_groups:
                summary += f" ({', '.join(failed_groups[:3])}{'...' if len(failed_groups) > 3 else ''})"

            self.log_msg(summary, color=COLORS["success"])
            self.log_msg("Đang dọn dẹp dữ liệu...", is_technical=True)
            self.app.clear_all_images()

            # Clear recovery state after successful completion
            try:
                recovery_manager.clear_recovery_state()
            except Exception as clear_err:
                self.log_msg(
                    f"⚠️ Warning: Could not clear recovery state: {clear_err}",
                    is_technical=True)

        except Exception as e:
            self.log_msg(f"Lỗi hệ thống: {str(e)}",
                         color=COLORS["error"], is_technical=True)
            final_status = "Failed"

        finally:
            # Clean up browser context
            try:
                if browser_context:
                    await browser_context.close()
                    self.log_msg("✓ Browser context closed", is_technical=True)
                if playwright_instance:
                    await playwright_instance.stop()
                    self.log_msg("✓ Playwright stopped", is_technical=True)
            except Exception as cleanup_error:
                self.log_msg(
                    f"Browser cleanup failed: {str(cleanup_error)}",
                    is_technical=True)

            # Reset instance variables
            self.pw_instance = None
            self.pw_context = None
            auto_runner.mark_finished()
            mod_guard.set_automation_running(False)

            # Update history
            if len(self.app.history_list_view.controls) > 0:
                self.app.history_list_view.controls.pop(0)
                job_data["status"] = final_status
                self.app.add_to_history(job_data)

            self.log_msg("Đã dừng tất cả hoạt động.",
                         color=COLORS["text_muted"], is_technical=True)
            await asyncio.sleep(2)
            self.app.page.update()

    async def _wait_for_login(self, page_pw, COLORS):
        """Wait for user to manually log in to Facebook if needed."""
        is_login_page = False
        try:
            is_login_page = "login" in page_pw.url
            if not is_login_page:
                try:
                    is_login_page = bool(await page_pw.query_selector("input[name='email']"))
                except Exception:
                    is_login_page = "login" in page_pw.url
        except Exception:
            is_login_page = "login" in page_pw.url

        if is_login_page:
            self.log_msg(
                "Đang chờ người dùng đăng nhập tay... Bạn có 120 giây.",
                color=COLORS["error"], is_technical=True)
            for _ in range(120):
                if not auto_runner.is_running():
                    return
                try:
                    still_login = "login" in page_pw.url
                    if not still_login:
                        try:
                            login_elem = await page_pw.query_selector("input[name='email']")
                            still_login = bool(login_elem)
                        except Exception:
                            still_login = False

                    if not still_login:
                        break
                except Exception:
                    break
                await asyncio.sleep(1)

            try:
                await page_pw.wait_for_selector('div[role="main"]', timeout=60000)
                timestamp = datetime.now().strftime("%H:%M")
                self.log_msg(
                    f"[{timestamp}] Đã nhận diện được trang chủ Facebook.",
                    color=COLORS["success"], is_technical=True)
            except Exception as e:
                self.log_msg(
                    f"Lỗi xác nhận sau khi đăng nhập (có thể context bị destroy): {str(e)[:50]}",
                    color=COLORS["error"], is_technical=True)
