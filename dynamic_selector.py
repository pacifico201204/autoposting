"""
Dynamic Selector Detection Module
Tự động phát hiện elements trên Facebook mà không cần hardcode
"""

from playwright.async_api import Page
import re
from logger_config import log_debug, log_error


class DynamicSelector:
    """Quản lý tìm kiếm dynamic elements"""

    def __init__(self, page: Page):
        self.page = page

    async def find_post_input_box(self):
        """
        Tìm ô nhập bài "Viết nội dung..." 
        Sử dụng nhiều phương pháp khác nhau
        """
        selectors_to_try = [
            # Method 1: By role + text (tiếng Việt + English)
            lambda: self.page.get_by_role("button", name=re.compile(
                r"Viết nội dung nào đó|Write something|Bạn đang nghĩ gì|on your mind",
                re.IGNORECASE
            )),

            # Method 2: By exact text
            lambda: self.page.locator('text="Write something..."'),
            lambda: self.page.locator('text="Viết nội dung nào đó..."'),

            # Method 3: By placeholder attribute
            lambda: self.page.locator(
                'input[placeholder*="Write"], input[placeholder*="Viết"]'),

            # Method 4: By aria-label
            lambda: self.page.locator(
                '[aria-label*="Write"], [aria-label*="Viết"]'),

            # Method 5: By class pattern (Facebook-style)
            lambda: self.page.locator(
                'div[role="button"] >> text=/Write something|Viết nội dung|Bạn đang nghĩ gì|Viết/i'),

            # Method 6: By contenteditable div
            lambda: self.page.locator(
                'div[contenteditable="true"][role="textbox"]'),
        ]

        for idx, selector_func in enumerate(selectors_to_try, 1):
            try:
                locator = selector_func()
                count = await locator.count()
                if count > 0:
                    log_debug(f"✓ Found post box using method {idx}")
                    return locator.first if count > 1 else locator
            except Exception as e:
                error_str = str(e)
                if "context" in error_str.lower() and "destroyed" in error_str.lower():
                    # Context destroyed, stop trying
                    log_debug(
                        f"✗ Method {idx} failed - context destroyed: {error_str[:50]}")
                    raise
                else:
                    log_debug(f"✗ Method {idx} failed: {error_str[:50]}")
                continue

        return None

    async def find_post_button(self):
        """
        Tìm nút "Đăng" (Post)
        Trong dialog/popup
        """
        selectors_to_try = [
            # Method 1: By aria-label
            lambda: self.page.locator(
                'div[role="dialog"] [aria-label*="Post"], [aria-label*="Đăng"]'),

            # Method 2: By text
            lambda: self.page.locator(
                'div[role="dialog"] button:has-text("Post")'),
            lambda: self.page.locator(
                'div[role="dialog"] button:has-text("Đăng")'),

            # Method 3: By class pattern
            lambda: self.page.locator(
                'div[role="dialog"] button:has-text(/Post|Đăng|Share/i)'),

            # Method 4: By data attribute
            lambda: self.page.locator(
                'button[data-testid*="post"], button[data-testid*="share"]'),

            # Method 5: Last button in dialog (usually Post button)
            lambda: self.page.locator('div[role="dialog"] button').last,
        ]

        for idx, selector_func in enumerate(selectors_to_try, 1):
            try:
                locator = selector_func()
                count = await locator.count()
                if count > 0:
                    log_debug(f"✓ Found post button using method {idx}")
                    return locator.first if count > 1 else locator
            except Exception as e:
                error_str = str(e)
                if "context" in error_str.lower() and "destroyed" in error_str.lower():
                    log_debug(
                        f"✗ Method {idx} failed - context destroyed: {error_str[:50]}")
                    raise
                else:
                    log_debug(f"✗ Method {idx} failed: {error_str[:50]}")
                continue

        return None

    async def find_file_input(self):
        """
        Tìm input[type="file"] để upload ảnh
        """
        selectors_to_try = [
            # Method 1: By accept attribute
            lambda: self.page.locator('input[type="file"][accept*="image"]'),

            # Method 2: By type only
            lambda: self.page.locator('input[type="file"]'),

            # Method 3: Hidden file input
            lambda: self.page.locator(
                'input[type="file"][style*="display: none"]'),

            # Method 4: By name attribute
            lambda: self.page.locator(
                'input[name*="upload"], input[name*="file"], input[name*="image"]'),
        ]

        for idx, selector_func in enumerate(selectors_to_try, 1):
            try:
                locator = selector_func()
                count = await locator.count()
                if count > 0:
                    log_debug(f"✓ Found file input using method {idx}")
                    return locator.last  # Thường là cái cuối cùng được thêm
            except Exception as e:
                error_str = str(e)
                if "context" in error_str.lower() and "destroyed" in error_str.lower():
                    log_debug(
                        f"✗ Method {idx} failed - context destroyed: {error_str[:50]}")
                    raise
                else:
                    log_debug(f"✗ Method {idx} failed: {error_str[:50]}")
                continue

        return None

    async def find_element_by_text(self, text_patterns: list, max_wait=5000):
        """
        Tìm element bằng text pattern
        text_patterns: list of regex patterns
        """
        combined_pattern = "|".join(text_patterns)

        try:
            locator = self.page.locator(f'text=/{combined_pattern}/i')
            if await locator.count() > 0:
                return locator.first
        except Exception as e:
            log_debug(f"Text search failed: {str(e)[:50]}")

        return None

    async def wait_for_main_content(self, timeout=30000):
        """
        Chờ trang chủ/nhóm load xong
        (main content area visible)
        """
        try:
            await self.page.wait_for_selector('div[role="main"]', timeout=timeout)
            return True
        except Exception as e:
            error_str = str(e)
            if "context" in error_str.lower() and "destroyed" in error_str.lower():
                # Context destroyed - page navigation happened
                print(
                    f"Context destroyed during wait_for_main_content: {error_str[:50]}")
                return False
            return False

    async def find_close_button_in_dialog(self):
        """
        Tìm nút đóng dialog (X button)
        """
        selectors_to_try = [
            # Method 1: aria-label
            lambda: self.page.locator(
                'div[role="dialog"] [aria-label="Close"]'),

            # Method 2: SVG close icon
            lambda: self.page.locator('div[role="dialog"] button >> svg'),

            # Method 3: Text Close
            lambda: self.page.locator(
                'div[role="dialog"] button:has-text("Close")'),
        ]

        for idx, selector_func in enumerate(selectors_to_try, 1):
            try:
                locator = selector_func()
                if await locator.count() > 0:
                    return locator.first
            except Exception:
                continue

        return None


async def get_dynamic_selector(page: Page) -> DynamicSelector:
    """Factory function để tạo DynamicSelector instance"""
    return DynamicSelector(page)
