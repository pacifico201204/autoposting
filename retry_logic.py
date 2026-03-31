"""
Retry Logic - Auto-retry failed operations with exponential backoff
Decorator for automatic retry of failed operations
Excludes system exceptions (Ctrl+C, shutdown) and caps maximum delay
"""

import asyncio
import functools
import random
from logger_config import log_warning, log_info, log_error


def retry_async(max_attempts=3, initial_delay=1, backoff_factor=2, max_delay=8):
    """
    Async retry decorator with exponential backoff and jitter

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1)
        backoff_factor: Multiplier for delay after each retry (default: 2)
        max_delay: Maximum delay cap to prevent unbounded waits (default: 8s)

    Usage:
        @retry_async(max_attempts=3, initial_delay=1)
        async def post_to_group(group_url):
            # Your posting code
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 1:
                        log_info(
                            f"✅ {func.__name__} succeeded on attempt {attempt}")
                    return result
                except (SystemExit, KeyboardInterrupt) as e:
                    # Don't retry system exceptions - let them propagate immediately
                    raise e
                except Exception as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # Calculate delay with exponential backoff and cap
                        delay = min(
                            initial_delay * (backoff_factor ** (attempt - 1)),
                            max_delay
                        )
                        # Add jitter (±20%) to prevent thundering herd
                        jitter = delay * random.uniform(0.8, 1.2)

                        log_warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {str(e)[:80]}"
                        )
                        log_info(f"⏳ Retrying in {jitter:.1f}s...")
                        await asyncio.sleep(jitter)
                    else:
                        log_error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )

            # If all attempts failed, raise the last exception
            raise last_exception

        return wrapper
    return decorator


def retry_sync(max_attempts=3, initial_delay=1, backoff_factor=2, max_delay=8):
    """
    Synchronous retry decorator with exponential backoff and jitter

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1)
        backoff_factor: Multiplier for delay after each retry (default: 2)
        max_delay: Maximum delay cap to prevent unbounded waits (default: 8s)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        log_info(
                            f"✅ {func.__name__} succeeded on attempt {attempt}")
                    return result
                except (SystemExit, KeyboardInterrupt) as e:
                    # Don't retry system exceptions - let them propagate immediately
                    raise e
                except Exception as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # Calculate delay with exponential backoff and cap
                        delay = min(
                            initial_delay * (backoff_factor ** (attempt - 1)),
                            max_delay
                        )
                        # Add jitter (±20%) to prevent thundering herd
                        jitter = delay * random.uniform(0.8, 1.2)

                        log_warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {str(e)[:80]}"
                        )
                        log_info(f"⏳ Retrying in {jitter:.1f}s...")
                        time.sleep(jitter)
                    else:
                        log_error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )

            raise last_exception

        return wrapper
    return decorator
