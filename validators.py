"""
Validators Module - Input validation for Vibecode Auto
Validate URLs, group names, post content, etc.
"""

import re
from urllib.parse import urlparse
from pathlib import Path
import os


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
