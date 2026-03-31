"""
Facebook Detection Limiter - Anti-detection safety measures
Giới hạn hoạt động để tránh bị Facebook detect bot
"""

from datetime import datetime, timedelta
from exceptions import TooManyPostsException, FacebookDetectionException


class DetectionLimiter:
    """
    Manages post limits and safety checks to prevent Facebook detection
    
    Safety Guidelines:
    - Max 10-15 posts per session
    - Max 25 posts per day
    - Min 15-30 minutes between sessions
    - Min 5 seconds between posts in same group
    """
    
    # Configuration constants
    MAX_POSTS_PER_SESSION = 10      # Conservative: 10 posts per run
    MAX_POSTS_PER_DAY = 25          # Daily limit: 25 posts/day
    MIN_DELAY_BETWEEN_SESSIONS = 5 * 60  # WARNING ONLY: 5 minutes (cho phép post, chỉ cảnh báo)
    MAX_DELAY_BETWEEN_SESSIONS = 30 * 60  # 30 minutes in seconds
    MIN_DELAY_BETWEEN_POSTS = 5  # Minimum 5 seconds between posts
    
    def __init__(self):
        """Initialize detection limiter with tracking data"""
        self.posts_today = 0
        self.posts_this_session = 0
        self.last_session_time = None
        self.today_date = datetime.now().date()
        self.session_start_time = datetime.now()
    
    def check_session_can_start(self) -> dict:
        """
        Check if a new session can start
        
        Returns:
            dict with 'can_start' (bool) and 'reason' (str)
        """
        # Reset daily counter if it's a new day
        if datetime.now().date() > self.today_date:
            self.posts_today = 0
            self.today_date = datetime.now().date()
        
        # Check if too many posts today
        if self.posts_today >= self.MAX_POSTS_PER_DAY:
            return {
                'can_start': False,
                'warning': True,
                'reason': f"⚠️ Đã đăng {self.posts_today}/{self.MAX_POSTS_PER_DAY} bài hôm nay. Hãy quay lại vào ngày mai."
            }
        
        # Check if enough time since last session (WARNING ONLY - allow to continue but warn)
        if self.last_session_time:
            time_since_last = datetime.now() - self.last_session_time
            if time_since_last.total_seconds() < self.MIN_DELAY_BETWEEN_SESSIONS:
                remaining = self.MIN_DELAY_BETWEEN_SESSIONS - time_since_last.total_seconds()
                minutes = int(remaining / 60)
                return {
                    'can_start': True,  # Changed: Allow to continue despite warning
                    'warning': True,
                    'reason': f"⚠️ Cảnh báo: Chỉ {int(time_since_last.total_seconds()/60)} phút kể từ lần cuối. (Facebook có thể detect bot nếu quá som)."
                }
        
        # Safe to start
        return {
            'can_start': True,
            'warning': False,
            'reason': f"✅ Có thể chạy. Đã đăng {self.posts_today}/{self.MAX_POSTS_PER_DAY} bài hôm nay."
        }
    
    def check_can_post_in_group(self, group_name: str) -> dict:
        """
        Check if can post in a specific group
        
        Args:
            group_name: Name of the group
            
        Returns:
            dict with 'can_post' (bool) and 'reason' (str)
        """
        # Check session limit
        if self.posts_this_session >= self.MAX_POSTS_PER_SESSION:
            return {
                'can_post': False,
                'warning': True,
                'reason': f"⚠️ Đã đạt giới hạn {self.MAX_POSTS_PER_SESSION} bài mỗi session. Dừng để an toàn."
            }
        
        # Check daily limit
        if self.posts_today >= self.MAX_POSTS_PER_DAY:
            return {
                'can_post': False,
                'warning': True,
                'reason': f"⚠️ Đã đạt giới hạn {self.MAX_POSTS_PER_DAY} bài mỗi ngày."
            }
        
        # Safe to post
        return {
            'can_post': True,
            'warning': False,
            'reason': f"✅ Có thể đăng trong '{group_name}'"
        }
    
    def record_post_success(self):
        """Record a successful post"""
        self.posts_this_session += 1
        self.posts_today += 1
    
    def record_session_start(self):
        """Record session start"""
        self.session_start_time = datetime.now()
        self.posts_this_session = 0
    
    def record_session_end(self):
        """Record session end"""
        self.last_session_time = datetime.now()
    
    def get_stats(self) -> dict:
        """Get current stats"""
        return {
            'posts_this_session': self.posts_this_session,
            'posts_today': self.posts_today,
            'max_posts_per_session': self.MAX_POSTS_PER_SESSION,
            'max_posts_per_day': self.MAX_POSTS_PER_DAY,
            'session_duration_seconds': (datetime.now() - self.session_start_time).total_seconds() if self.session_start_time else 0
        }
    
    def get_daily_summary(self) -> str:
        """Get human-readable daily summary"""
        posts_left_today = self.MAX_POSTS_PER_DAY - self.posts_today
        return f"📊 {self.posts_today}/{self.MAX_POSTS_PER_DAY} bài hôm nay | {posts_left_today} bài còn lại"
    
    def get_session_summary(self) -> str:
        """Get human-readable session summary"""
        posts_left_session = self.MAX_POSTS_PER_SESSION - self.posts_this_session
        return f"📊 {self.posts_this_session}/{self.MAX_POSTS_PER_SESSION} bài session này | {posts_left_session} bài còn lại"
