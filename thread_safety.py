"""
Thread Safety Module - Xử lý race condition & thread synchronization

Giải quyết vấn đề:
- Multiple async tasks chạy cùng lúc
- Update history & groups cùng lúc
- UI & logic race condition

Solutions:
- Lock mechanism cho shared resources
- Atomic operations
- Thread-safe queue
"""

import asyncio
import threading
from typing import Any, Callable, Awaitable
import time


class ThreadSafeAutoRunner:
    """
    Thread-safe automation runner - Đảm bảo chỉ 1 automation chạy tại 1 lúc
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._is_running = False
        self._current_thread = None
        
    def is_running(self) -> bool:
        """Check if automation is running (thread-safe)"""
        with self._lock:
            return self._is_running
    
    def can_start(self) -> bool:
        """Check if can start new automation (thread-safe)"""
        with self._lock:
            if self._is_running:
                return False
            self._is_running = True
            self._current_thread = threading.current_thread()
            return True
    
    def mark_finished(self):
        """Mark automation as finished (thread-safe)"""
        with self._lock:
            self._is_running = False
            self._current_thread = None
    
    def stop(self):
        """Stop current running automation (thread-safe)"""
        with self._lock:
            self._is_running = False
    
    def __enter__(self):
        """Context manager - start"""
        if not self.can_start():
            raise RuntimeError("❌ Automation đang chạy rồi! Vui lòng chờ finish.")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - stop"""
        self.mark_finished()
        return False


class ThreadSafeStorage:
    """
    Thread-safe wrapper cho storage operations
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._cache = {}
        self._dirty = False  # Track if data changed
    
    def read_with_lock(self, read_func: Callable) -> Any:
        """
        Read data with lock (thread-safe)
        
        Args:
            read_func: Function that reads data
            
        Returns:
            Data from read_func
        """
        with self._lock:
            return read_func()
    
    def write_with_lock(self, write_func: Callable) -> Any:
        """
        Write data with lock (thread-safe)
        
        Args:
            write_func: Function that writes data
            
        Returns:
            Result from write_func
        """
        with self._lock:
            result = write_func()
            self._dirty = True
            return result
    
    def cache_get(self, key: str) -> Any:
        """Get from cache (thread-safe)"""
        with self._lock:
            return self._cache.get(key)
    
    def cache_set(self, key: str, value: Any):
        """Set cache (thread-safe)"""
        with self._lock:
            self._cache[key] = value
            self._dirty = True
    
    def is_dirty(self) -> bool:
        """Check if data changed (thread-safe)"""
        with self._lock:
            return self._dirty
    
    def mark_clean(self):
        """Mark data as clean (thread-safe)"""
        with self._lock:
            self._dirty = False


class AsyncQueueRunner:
    """
    Async task queue - Prevent concurrent operations
    
    Sử dụng:
    queue = AsyncQueueRunner()
    await queue.add_task(async_func, arg1, arg2)
    """
    
    def __init__(self, max_queue_size: int = 100):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._current_task = None
    
    async def start(self):
        """Start queue processor"""
        self._running = True
        while self._running:
            try:
                task_func, args, kwargs = await asyncio.wait_for(
                    self._queue.get(), 
                    timeout=1.0
                )
                self._current_task = task_func
                await task_func(*args, **kwargs)
                self._current_task = None
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Queue error: {e}")
                self._current_task = None
    
    async def stop(self):
        """Stop queue processor"""
        self._running = False
        # Wait for current task to finish
        timeout = 5  # 5 seconds
        start = time.time()
        while self._current_task and (time.time() - start) < timeout:
            await asyncio.sleep(0.1)
    
    async def add_task(self, func: Callable[..., Awaitable], *args, **kwargs):
        """
        Add task to queue
        
        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        try:
            await asyncio.wait_for(
                self._queue.put((func, args, kwargs)),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            raise RuntimeError("❌ Queue full! Task bị từ chối.")
    
    async def wait_for_idle(self, timeout: float = 10.0):
        """
        Wait for queue to be empty (all tasks done)
        
        Args:
            timeout: Max wait time in seconds
        """
        start = time.time()
        while not self._queue.empty() and (time.time() - start) < timeout:
            await asyncio.sleep(0.1)
    
    def is_busy(self) -> bool:
        """Check if queue has pending tasks"""
        return not self._queue.empty() or self._current_task is not None


class DataModificationGuard:
    """
    Prevent modification of data while automation running
    
    Sử dụng:
    guard = DataModificationGuard()
    
    # In UI modification code:
    if not guard.can_modify():
        show_error("❌ Không thể modify khi automation chạy!")
        return
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._automation_running = False
    
    def set_automation_running(self, running: bool):
        """Set automation state (thread-safe)"""
        with self._lock:
            self._automation_running = running
    
    def can_modify(self) -> bool:
        """Check if data can be modified (thread-safe)"""
        with self._lock:
            return not self._automation_running
    
    def must_be_idle(self, operation_name: str):
        """
        Raise if automation running (thread-safe)
        
        Args:
            operation_name: Name of operation for error message
        """
        with self._lock:
            if self._automation_running:
                raise RuntimeError(
                    f"❌ {operation_name} không được phép chạy khi automation đang hoạt động!"
                )


# Global instances (singleton pattern)
_auto_runner = None
_storage = None
_queue_runner = None
_modification_guard = None


def get_auto_runner() -> ThreadSafeAutoRunner:
    """Get global auto runner instance"""
    global _auto_runner
    if _auto_runner is None:
        _auto_runner = ThreadSafeAutoRunner()
    return _auto_runner


def get_storage() -> ThreadSafeStorage:
    """Get global storage instance"""
    global _storage
    if _storage is None:
        _storage = ThreadSafeStorage()
    return _storage


def get_queue_runner() -> AsyncQueueRunner:
    """Get global queue runner instance"""
    global _queue_runner
    if _queue_runner is None:
        _queue_runner = AsyncQueueRunner()
    return _queue_runner


def get_modification_guard() -> DataModificationGuard:
    """Get global modification guard instance"""
    global _modification_guard
    if _modification_guard is None:
        _modification_guard = DataModificationGuard()
    return _modification_guard


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: ThreadSafeAutoRunner - Ensure only 1 automation runs
----
def start_automation():
    runner = get_auto_runner()
    
    try:
        if not runner.can_start():
            print("❌ Automation đang chạy rồi!")
            return
        
        # Run automation
        run_auto()
    finally:
        runner.mark_finished()

EXAMPLE 2: ThreadSafeStorage - Thread-safe data access
----
storage = get_storage()

# Read safely
groups = storage.read_with_lock(lambda: load_groups())

# Write safely
storage.write_with_lock(lambda: save_groups(new_groups))

# Cache
storage.cache_set("posts_today", 5)
count = storage.cache_get("posts_today")

EXAMPLE 3: DataModificationGuard - Prevent editing while running
----
guard = get_modification_guard()

def on_delete_group(e):
    try:
        guard.must_be_idle("Delete group")
        # Safe to delete
        delete_group(group_id)
    except RuntimeError as err:
        show_error(str(err))

def start_auto():
    guard.set_automation_running(True)
    try:
        run_automation()
    finally:
        guard.set_automation_running(False)

EXAMPLE 4: AsyncQueueRunner - Queue tasks
----
queue = get_queue_runner()

async def start_queue():
    # Start queue processor in background
    asyncio.create_task(queue.start())

async def add_some_tasks():
    await queue.add_task(post_to_group, "group1", "content")
    await queue.add_task(post_to_group, "group2", "content")
    
    # Wait for all tasks to finish
    await queue.wait_for_idle()
"""
