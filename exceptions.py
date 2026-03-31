"""
Custom Exceptions for Auto Posting
Định nghĩa các exception riêng để xử lý lỗi cụ thể
"""


class AutoPostingException(Exception):
    """Base exception for all Auto Posting errors"""
    pass


class FacebookDetectionException(AutoPostingException):
    """Raised when Facebook might be detecting bot activity"""
    pass


class BrowserContextException(AutoPostingException):
    """Raised when browser context has issues"""
    pass


class ContextDestroyedException(BrowserContextException):
    """Raised when browser context is destroyed"""
    pass


class PlaywrightException(BrowserContextException):
    """Raised when Playwright encounters errors"""
    pass


class ElementNotFoundException(AutoPostingException):
    """Raised when expected element is not found"""
    pass


class LoginRequiredException(AutoPostingException):
    """Raised when login is required"""
    pass


class TooManyPostsException(FacebookDetectionException):
    """Raised when daily post limit is exceeded"""
    pass


class ValidationException(AutoPostingException):
    """Raised when input validation fails"""
    pass
