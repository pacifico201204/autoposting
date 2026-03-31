"""
Anti-Detection Enhancements - Tier 1 (Easy, High Impact)
Các cải thiện đơn giản nhưng rất hiệu quả để tránh detect
"""

import random
import asyncio


class BrowserFingerprint:
    """Randomize browser fingerprint to avoid detection"""
    
    # Real user agents từ các thiết bị khác nhau
    USER_AGENTS = [
        # Windows Chrome (Desktop)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Windows Firefox (Desktop)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # macOS Chrome (Desktop)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # macOS Safari (Desktop)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Linux Chrome (Desktop)
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # iPhone Safari (Mobile)
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        # Android Chrome (Mobile)
        "Mozilla/5.0 (Linux; Android 13; SM-A135F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        # iPad Safari (Tablet)
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    ]
    
    @staticmethod
    def get_random_user_agent():
        """Get random user agent to rotate"""
        return random.choice(BrowserFingerprint.USER_AGENTS)
    
    @staticmethod
    async def apply_fingerprint(page):
        """
        Apply anti-detection fingerprint spoofing
        Che giấu các dấu hiệu của automation
        """
        try:
            await page.evaluate("""
                // Hide webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Fake plugins array
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Set languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Fake languages property
                Object.defineProperty(navigator, 'language', {
                    get: () => 'en-US',
                });
                
                // Chrome specific
                window.chrome = {
                    runtime: {}
                };
                
                // Remove headless property
                if (navigator.userAgentData) {
                    Object.defineProperty(navigator, 'userAgentData', {
                        get: () => ({
                            platform: 'Windows',
                            platformVersion: '10.0',
                        })
                    });
                }
                
                // Fix permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
                );
            """)
            return True
        except Exception as e:
            print(f"❌ Error applying fingerprint: {e}")
            return False


class MouseBehavior:
    """Simulate realistic mouse movement and scrolling"""
    
    @staticmethod
    async def random_scroll(page, min_scroll=-500, max_scroll=500):
        """
        Scroll trang ngẫu nhiên (giống như người đang đọc)
        
        Args:
            page: Playwright page object
            min_scroll: Min scroll pixels
            max_scroll: Max scroll pixels
        """
        try:
            scroll_amount = random.randint(min_scroll, max_scroll)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 2.0))
            return True
        except Exception as e:
            print(f"❌ Error scrolling: {e}")
            return False
    
    @staticmethod
    async def move_mouse_to_element(page, selector):
        """
        Move mouse to element trước khi tương tác
        Làm cho behavior trông giống người
        
        Args:
            page: Playwright page object
            selector: CSS selector of element
        """
        try:
            element = await page.query_selector(selector)
            if element:
                # Get element position
                box = await element.bounding_box()
                if box:
                    # Move mouse to element with random jitter
                    x = box['x'] + box['width']/2 + random.uniform(-10, 10)
                    y = box['y'] + box['height']/2 + random.uniform(-10, 10)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.2, 0.8))
                    return True
        except Exception as e:
            print(f"❌ Error moving mouse: {e}")
        
        return False
    
    @staticmethod
    async def scroll_to_element(page, selector):
        """Scroll to element naturally"""
        try:
            await page.evaluate(f"""
                const el = document.querySelector('{selector}');
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            """)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            return True
        except Exception as e:
            print(f"❌ Error scrolling to element: {e}")
            return False


class TypingBehavior:
    """Simulate human-like typing patterns"""
    
    # Typing profiles for different typing speeds
    TYPING_PROFILES = {
        'fast': (0.05, 0.12),      # 50-120ms per char (fast typer)
        'normal': (0.08, 0.15),    # 80-150ms per char (average)
        'slow': (0.12, 0.25),      # 120-250ms per char (slow typer)
        'variable': (0.05, 0.25),  # Highly variable (very human-like)
    }
    
    def __init__(self, profile='variable'):
        """
        Initialize typing behavior
        
        Args:
            profile: 'fast', 'normal', 'slow', or 'variable'
        """
        self.profile = profile
        self.min_delay, self.max_delay = self.TYPING_PROFILES.get(profile, self.TYPING_PROFILES['variable'])
    
    async def type_text(self, page, text, log_callback=None):
        """
        Type text with human-like behavior
        
        Args:
            page: Playwright page object
            text: Text to type
            log_callback: Function to call for logging
        """
        for i, char in enumerate(text):
            try:
                # 5% chance to type wrong character (human-like typo)
                if random.random() < 0.05 and char.isalpha():
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    await page.keyboard.type(wrong_char)
                    await asyncio.sleep(random.uniform(0.1, 0.4))
                    
                    # Fix typo with backspace
                    await page.keyboard.press("Backspace")
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    if log_callback:
                        log_callback(f"Typed wrong, fixed: {wrong_char} → {char}", is_technical=True)
                
                # Type correct character
                await page.keyboard.type(char)
                
                # Random typing delay
                base_delay = random.uniform(self.min_delay, self.max_delay)
                
                # 3% chance of random pause (thinking)
                if random.random() < 0.03:
                    pause_time = random.uniform(0.5, 3.0)
                    if log_callback:
                        log_callback(f"Thinking pause: {pause_time:.1f}s", is_technical=True)
                    await asyncio.sleep(pause_time)
                    continue
                
                # Occasional longer pause between words
                if char == ' ' and random.random() < 0.15:
                    pause_time = random.uniform(0.5, 1.5)
                    await asyncio.sleep(pause_time)
                    continue
                
                # Normal typing delay
                await asyncio.sleep(base_delay)
                
            except Exception as e:
                print(f"❌ Error typing character: {e}")
                return False
        
        return True


class AntiDetectionManager:
    """Main manager for all anti-detection features"""
    
    def __init__(self, log_callback=None):
        """
        Initialize anti-detection manager
        
        Args:
            log_callback: Function to call for logging messages
        """
        self.log_callback = log_callback
        self.typing_behavior = TypingBehavior(profile='variable')
    
    async def setup_page(self, page):
        """
        Setup page with all anti-detection measures
        
        Args:
            page: Playwright page object
            
        Returns:
            bool: Success status
        """
        success = True
        
        # Apply fingerprint spoofing
        if not await BrowserFingerprint.apply_fingerprint(page):
            success = False
        
        # Optional: Add some random delays to make page load more human-like
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return success
    
    async def scroll_like_human(self, page):
        """Scroll page like human reading"""
        # Random scroll up/down
        await MouseBehavior.random_scroll(page, -300, 500)
    
    async def type_post_content(self, page, selector, content):
        """
        Type post content with human-like behavior
        
        Args:
            page: Playwright page object
            selector: CSS selector of input field
            content: Text content to type
            
        Returns:
            bool: Success status
        """
        try:
            # Find the input field
            await page.click(selector)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Type the content
            return await self.typing_behavior.type_text(page, content, self.log_callback)
        
        except Exception as e:
            print(f"❌ Error typing content: {e}")
            return False
    
    def log_msg(self, message, is_technical=False):
        """Log message if callback provided"""
        if self.log_callback:
            self.log_callback(message, is_technical=is_technical)


# Quick helper functions
async def setup_anti_detection(page):
    """One-line setup of anti-detection"""
    return await BrowserFingerprint.apply_fingerprint(page)


def get_random_user_agent():
    """Get random user agent"""
    return BrowserFingerprint.get_random_user_agent()


async def type_like_human(page, text, log_callback=None):
    """Type text like human"""
    typer = TypingBehavior()
    return await typer.type_text(page, text, log_callback)
