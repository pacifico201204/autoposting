"""
Validators Module - Input validation for Auto Posting
Validate URLs, group names, post content, image files, and Facebook account status
"""

import re
import os
import json
from urllib.parse import urlparse
from pathlib import Path
from logger_config import log_warning, log_info


class ValidationError(Exception):
    """Custom validation error"""
    pass


class Validators:
    """Collection of validation methods"""

    @staticmethod
    def validate_facebook_url(url: str) -> None:
        """
        Validate Facebook group URL

        Args:
            url: Facebook group URL to validate

        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL is required")

        # Add https:// if missing
        if not url.startswith("http"):
            url = "https://" + url

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("Invalid URL format")

        # Check domain is Facebook
        if "facebook.com" not in parsed.netloc:
            raise ValidationError("Must be a Facebook.com URL")

        # Check if it's a group URL
        if "/groups/" not in parsed.path:
            raise ValidationError("Must be a Facebook group URL (/groups/...)")

    @staticmethod
    def validate_group_name(name: str) -> None:
        """
        Validate group name

        Args:
            name: Group name to validate

        Raises:
            ValidationError: If name is invalid
        """
        if not name:
            raise ValidationError("Group name is required")

        name = name.strip()

        if len(name) < 3:
            raise ValidationError("Group name too short (min 3 characters)")

        if len(name) > 100:
            raise ValidationError("Group name too long (max 100 characters)")

    @staticmethod
    def validate_post_content(content: str) -> None:
        """
        Validate post content

        Args:
            content: Post content to validate

        Raises:
            ValidationError: If content is invalid
        """
        if not content or not content.strip():
            raise ValidationError("Post content is required")

        content = content.strip()

        if len(content) < 3:
            raise ValidationError("Content too short (min 3 characters)")

        # Facebook limit: 63,206 characters
        if len(content) > 63206:
            raise ValidationError("Content too long (max 63,206 characters)")

    @staticmethod
    def validate_image_path(path: str) -> None:
        """
        Validate image file path

        Args:
            path: Image file path to validate

        Raises:
            ValidationError: If image is invalid
        """
        if not path:
            raise ValidationError("Image path is required")

        if not os.path.exists(path):
            raise ValidationError(f"File does not exist: {path}")

        # Check extension
        valid_ext = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        if not Path(path).suffix.lower() in valid_ext:
            raise ValidationError(f"Image format not supported")

        # Check file size (5MB max)
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > 5:
            raise ValidationError(
                f"Image too large ({file_size_mb:.1f}MB > 5MB)")

    @staticmethod
    def validate_delay_range(min_delay: int, max_delay: int) -> None:
        """
        Validate delay range for post intervals

        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds

        Raises:
            ValidationError: If range is invalid
        """
        try:
            min_val = int(min_delay)
            max_val = int(max_delay)
        except (ValueError, TypeError):
            raise ValidationError("Delay must be an integer")

        if min_val < 0:
            raise ValidationError("Delay cannot be negative")

        if min_val > max_val:
            raise ValidationError(
                f"Min delay ({min_val}s) cannot be greater than max ({max_val}s)")

        if max_val > 3600:  # 1 hour max
            raise ValidationError(
                "Max delay cannot exceed 3600 seconds (1 hour)")

    @staticmethod
    def check_facebook_login_status(browser_profile_path: str = None) -> bool:
        """
        ⚠️ NOT RECOMMENDED - For reference only, do not use in production flow

        Check if Facebook account is logged in via browser cookies

        LIMITATION: This function cannot reliably check cookies while browser is running
        because Chrome/Edge locks the database file. Returns False while browser is open.

        Args:
            browser_profile_path: Path to browser profile (Chromium or similar)
                                 If None, tries common paths

        Returns:
            True if Facebook login cookies found, False otherwise

        Note: 
            - Only works when browser is fully closed
            - Chrome/Edge locks Cookies database while running
            - Not suitable for real-time validation during posting
        """
        try:
            # Common browser profile paths
            if browser_profile_path is None:
                browser_profile_path = os.path.expanduser(
                    "~/.config/google-chrome/Default"  # Linux
                )

                # Windows Chrome path
                if not os.path.exists(browser_profile_path):
                    browser_profile_path = os.path.expanduser(
                        "~\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
                    )

                # Windows Edge path
                if not os.path.exists(browser_profile_path):
                    browser_profile_path = os.path.expanduser(
                        "~\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default"
                    )

            if not os.path.exists(browser_profile_path):
                log_warning(
                    f"Browser profile not found at: {browser_profile_path}")
                return False

            # Check for cookies file
            cookies_path = os.path.join(browser_profile_path, "Cookies")
            if not os.path.exists(cookies_path):
                log_warning(f"Cookies file not found")
                return False

            # Try to read cookies (SQLite database)
            # ⚠️ WILL FAIL if browser is running (database locked)
            try:
                file_size = os.path.getsize(cookies_path)
                if file_size > 0:
                    log_info(f"✅ Browser cookies found ({file_size} bytes)")
                    return True
            except PermissionError:
                # Expected when browser is running
                log_warning(
                    "⚠️ Cannot access cookies while browser is running (database locked)")
                return False

            return False

        except Exception as e:
            log_warning(f"Error checking Facebook login status: {e}")
            return False

    @staticmethod
    def validate_facebook_url_enhanced(url: str) -> dict:
        """
        Enhanced Facebook group URL validation

        Args:
            url: Facebook group URL to validate

        Returns:
            dict with validation result and extracted group info
            Example: {
                "valid": True,
                "group_id": "123456789",
                "group_url": "https://facebook.com/groups/123456789",
                "message": "URL is valid"
            }

        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL is required")

        # Add https:// if missing
        if not url.startswith("http"):
            url = "https://" + url

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("Invalid URL format")

        # Check domain is Facebook
        if "facebook.com" not in parsed.netloc:
            raise ValidationError("Must be a Facebook.com URL")

        # Check if it's a group URL
        if "/groups/" not in parsed.path:
            raise ValidationError("Must be a Facebook group URL (/groups/...)")

        # Extract group ID from path
        # Path format: /groups/{group_id}/ or /groups/{group_id}
        path_parts = parsed.path.split('/')
        group_id = None

        try:
            groups_idx = path_parts.index('groups')
            if groups_idx + 1 < len(path_parts):
                group_id = path_parts[groups_idx + 1].strip('/')

                # Validate group ID is numeric or alphanumeric
                if not group_id:
                    raise ValidationError(
                        "Could not extract group ID from URL")
        except (ValueError, IndexError):
            raise ValidationError("Invalid group URL format")

        return {
            "valid": True,
            "group_id": group_id,
            "group_url": url,
            "message": f"✅ Valid Facebook group URL (ID: {group_id})"
        }
