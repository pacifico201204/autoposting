"""
Custom Exceptions for Vibecode Auto
Định nghĩa các exception riêng để xử lý lỗi cụ thể
"""


class VibecodeException(Exception):
    """Base exception for all Vibecode errors"""
    pass


class FacebookDetectionException(VibecodeException):
    """Raised when Facebook might be detecting bot activity"""
    pass


class BrowserContextException(VibecodeException):
    """Raised when browser context has issues"""
    pass


class ContextDestroyedException(BrowserContextException):
    """Raised when browser context is destroyed"""
    pass


class PlaywrightException(BrowserContextException):
    """Raised when Playwright encounters errors"""
    pass


class ElementNotFoundException(VibecodeException):
    """Raised when expected element is not found"""
    pass


class LoginRequiredException(VibecodeException):
    """Raised when login is required"""
    pass


class TooManyPostsException(FacebookDetectionException):
    """Raised when daily post limit is exceeded"""
    pass


class ValidationException(VibecodeException):
    """Raised when input validation fails"""
    pass
