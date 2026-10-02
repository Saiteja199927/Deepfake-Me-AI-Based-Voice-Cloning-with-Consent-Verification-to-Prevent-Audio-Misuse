"""
Rate Limiter and Usage Tracker Module
Controls API usage and tracks user activity for resource management
"""

import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from enum import Enum


class RateLimitTier(Enum):
    """User tier for rate limiting."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass
class RateLimitConfig:
    """Configuration for rate limits per tier."""
    tier: RateLimitTier
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    requests_per_day: int = 500
    max_characters_per_request: int = 5000
    max_audio_duration_seconds: int = 300
    max_file_size_mb: int = 50
    
    @classmethod
    def get_tier_config(cls, tier: RateLimitTier) -> 'RateLimitConfig':
        """Get rate limit config for a tier."""
        configs = {
            RateLimitTier.FREE: cls(
                tier=RateLimitTier.FREE,
                requests_per_minute=5,
                requests_per_hour=30,
                requests_per_day=100,
                max_characters_per_request=1000,
                max_audio_duration_seconds=60,
                max_file_size_mb=10
            ),
            RateLimitTier.BASIC: cls(
                tier=RateLimitTier.BASIC,
                requests_per_minute=15,
                requests_per_hour=200,
                requests_per_day=1000,
                max_characters_per_request=5000,
                max_audio_duration_seconds=300,
                max_file_size_mb=50
            ),
            RateLimitTier.PREMIUM: cls(
                tier=RateLimitTier.PREMIUM,
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=5000,
                max_characters_per_request=10000,
                max_audio_duration_seconds=600,
                max_file_size_mb=100
            ),
            RateLimitTier.ENTERPRISE: cls(
                tier=RateLimitTier.ENTERPRISE,
                requests_per_minute=100,
                requests_per_hour=2000,
                requests_per_day=20000,
                max_characters_per_request=50000,
                max_audio_duration_seconds=3600,
                max_file_size_mb=500
            ),
            RateLimitTier.UNLIMITED: cls(
                tier=RateLimitTier.UNLIMITED,
                requests_per_minute=999999,
                requests_per_hour=999999,
                requests_per_day=999999,
                max_characters_per_request=999999,
                max_audio_duration_seconds=999999,
                max_file_size_mb=999999
            )
        }
        return configs.get(tier, configs[RateLimitTier.FREE])


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    user_id: str
    tier: RateLimitTier
    remaining_minute: int = 0
    remaining_hour: int = 0
    remaining_day: int = 0
    reset_time_seconds: int = 0
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'allowed': self.allowed,
            'user_id': self.user_id,
            'tier': self.tier.value,
            'remaining_minute': self.remaining_minute,
            'remaining_hour': self.remaining_hour,
            'remaining_day': self.remaining_day,
            'reset_time_seconds': self.reset_time_seconds,
            'reason': self.reason,
            'metadata': self.metadata
        }


@dataclass
class UsageStats:
    """Usage statistics for a user."""
    user_id: str
    total_requests: int = 0
    total_characters: int = 0
    total_audio_seconds: float = 0.0
    total_file_size_mb: float = 0.0
    requests_today: int = 0
    requests_this_hour: int = 0
    requests_this_minute: int = 0
    last_request_time: Optional[str] = None
    first_request_time: Optional[str] = None
    tier: RateLimitTier = RateLimitTier.FREE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'total_requests': self.total_requests,
            'total_characters': self.total_characters,
            'total_audio_seconds': self.total_audio_seconds,
            'total_file_size_mb': self.total_file_size_mb,
            'requests_today': self.requests_today,
            'requests_this_hour': self.requests_this_hour,
            'requests_this_minute': self.requests_this_minute,
            'last_request_time': self.last_request_time,
            'first_request_time': self.first_request_time,
            'tier': self.tier.value
        }


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.
    
    Features:
    - Per-user rate limiting
    - Multiple time windows (minute, hour, day)
    - Tier-based limits
    - Thread-safe operation
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        default_tier: RateLimitTier = RateLimitTier.FREE
    ):
        """
        Initialize Rate Limiter.
        
        Args:
            storage_dir: Directory for persistent storage
            default_tier: Default tier for new users
        """
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/rate_limits")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.default_tier = default_tier
        
        # Request timestamps per user
        # Structure: {user_id: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, List[float]] = defaultdict(list)
        
        # User tiers
        self._user_tiers: Dict[str, RateLimitTier] = {}
        
        # Rate limit configs
        self._configs: Dict[RateLimitTier, RateLimitConfig] = {
            tier: RateLimitConfig.get_tier_config(tier)
            for tier in RateLimitTier
        }
        
        # Thread lock
        self._lock = threading.Lock()
        
        # Load persisted data
        self._load_user_tiers()
    
    def _load_user_tiers(self) -> None:
        """Load user tiers from storage."""
        tiers_file = self.storage_dir / "user_tiers.json"
        if tiers_file.exists():
            try:
                data = json.loads(tiers_file.read_text())
                self._user_tiers = {
                    user_id: RateLimitTier(tier)
                    for user_id, tier in data.items()
                }
            except:
                pass
    
    def _save_user_tiers(self) -> None:
        """Save user tiers to storage."""
        tiers_file = self.storage_dir / "user_tiers.json"
        data = {
            user_id: tier.value
            for user_id, tier in self._user_tiers.items()
        }
        tiers_file.write_text(json.dumps(data, indent=2))
    
    def _clean_old_requests(self, user_id: str) -> None:
        """Remove requests older than 24 hours."""
        cutoff = time.time() - 86400  # 24 hours ago
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] if ts > cutoff
        ]
    
    def check_rate_limit(self, user_id: str) -> RateLimitResult:
        """
        Check if a user can make a request.
        
        Args:
            user_id: User identifier
            
        Returns:
            RateLimitResult indicating if request is allowed
        """
        with self._lock:
            now = time.time()
            
            # Clean old requests
            self._clean_old_requests(user_id)
            
            # Get user tier and config
            tier = self._user_tiers.get(user_id, self.default_tier)
            config = self._configs[tier]
            
            # Get request timestamps
            requests = self._requests[user_id]
            
            # Count requests in each window
            minute_ago = now - 60
            hour_ago = now - 3600
            day_ago = now - 86400
            
            requests_minute = sum(1 for ts in requests if ts > minute_ago)
            requests_hour = sum(1 for ts in requests if ts > hour_ago)
            requests_day = sum(1 for ts in requests if ts > day_ago)
            
            # Check limits
            if requests_minute >= config.requests_per_minute:
                # Find oldest request in the minute window
                oldest_in_minute = min([ts for ts in requests if ts > minute_ago], default=now)
                reset_time = int(60 - (now - oldest_in_minute))
                
                return RateLimitResult(
                    allowed=False,
                    user_id=user_id,
                    tier=tier,
                    remaining_minute=0,
                    remaining_hour=max(0, config.requests_per_hour - requests_hour),
                    remaining_day=max(0, config.requests_per_day - requests_day),
                    reset_time_seconds=max(1, reset_time),
                    reason="Rate limit exceeded (per minute)"
                )
            
            if requests_hour >= config.requests_per_hour:
                oldest_in_hour = min([ts for ts in requests if ts > hour_ago], default=now)
                reset_time = int(3600 - (now - oldest_in_hour))
                
                return RateLimitResult(
                    allowed=False,
                    user_id=user_id,
                    tier=tier,
                    remaining_minute=max(0, config.requests_per_minute - requests_minute),
                    remaining_hour=0,
                    remaining_day=max(0, config.requests_per_day - requests_day),
                    reset_time_seconds=max(1, reset_time),
                    reason="Rate limit exceeded (per hour)"
                )
            
            if requests_day >= config.requests_per_day:
                oldest_in_day = min([ts for ts in requests if ts > day_ago], default=now)
                reset_time = int(86400 - (now - oldest_in_day))
                
                return RateLimitResult(
                    allowed=False,
                    user_id=user_id,
                    tier=tier,
                    remaining_minute=max(0, config.requests_per_minute - requests_minute),
                    remaining_hour=max(0, config.requests_per_hour - requests_hour),
                    remaining_day=0,
                    reset_time_seconds=max(1, reset_time),
                    reason="Rate limit exceeded (per day)"
                )
            
            return RateLimitResult(
                allowed=True,
                user_id=user_id,
                tier=tier,
                remaining_minute=config.requests_per_minute - requests_minute - 1,
                remaining_hour=config.requests_per_hour - requests_hour - 1,
                remaining_day=config.requests_per_day - requests_day - 1,
                reset_time_seconds=0
            )
    
    def record_request(self, user_id: str) -> None:
        """Record a request for a user."""
        with self._lock:
            self._requests[user_id].append(time.time())
    
    def check_and_record(self, user_id: str) -> RateLimitResult:
        """
        Check rate limit and record request if allowed.
        
        Args:
            user_id: User identifier
            
        Returns:
            RateLimitResult
        """
        result = self.check_rate_limit(user_id)
        if result.allowed:
            self.record_request(user_id)
        return result
    
    def set_user_tier(self, user_id: str, tier: RateLimitTier) -> None:
        """Set the tier for a user."""
        with self._lock:
            self._user_tiers[user_id] = tier
            self._save_user_tiers()
    
    def get_user_tier(self, user_id: str) -> RateLimitTier:
        """Get the tier for a user."""
        return self._user_tiers.get(user_id, self.default_tier)
    
    def get_tier_config(self, tier: RateLimitTier) -> RateLimitConfig:
        """Get configuration for a tier."""
        return self._configs[tier]
    
    def reset_user_limits(self, user_id: str) -> None:
        """Reset rate limits for a user."""
        with self._lock:
            self._requests[user_id] = []


class UsageTracker:
    """
    Track and record user usage statistics.
    
    Features:
    - Per-user usage tracking
    - Multiple metrics (requests, characters, audio duration)
    - Historical data storage
    - Usage analytics
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize Usage Tracker.
        
        Args:
            storage_dir: Directory for persistent storage
            rate_limiter: Optional RateLimiter instance to integrate with
        """
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/usage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.rate_limiter = rate_limiter
        
        # User statistics
        self._user_stats: Dict[str, UsageStats] = {}
        
        # Usage history (for daily/monthly aggregation)
        self._usage_history: List[Dict[str, Any]] = []
        
        # Thread lock
        self._lock = threading.Lock()
        
        # Load persisted data
        self._load_stats()
    
    def _load_stats(self) -> None:
        """Load usage statistics from storage."""
        stats_file = self.storage_dir / "user_stats.json"
        if stats_file.exists():
            try:
                data = json.loads(stats_file.read_text())
                for user_id, stats_data in data.items():
                    stats_data['tier'] = RateLimitTier(stats_data.get('tier', 'free'))
                    self._user_stats[user_id] = UsageStats(**stats_data)
            except Exception as e:
                print(f"Error loading usage stats: {e}")
    
    def _save_stats(self) -> None:
        """Save usage statistics to storage."""
        stats_file = self.storage_dir / "user_stats.json"
        data = {
            user_id: stats.to_dict()
            for user_id, stats in self._user_stats.items()
        }
        stats_file.write_text(json.dumps(data, indent=2))
    
    def _get_or_create_stats(self, user_id: str) -> UsageStats:
        """Get or create usage stats for a user."""
        if user_id not in self._user_stats:
            tier = RateLimitTier.FREE
            if self.rate_limiter:
                tier = self.rate_limiter.get_user_tier(user_id)
            
            self._user_stats[user_id] = UsageStats(
                user_id=user_id,
                tier=tier,
                first_request_time=datetime.now(timezone.utc).isoformat()
            )
        return self._user_stats[user_id]
    
    def record_usage(
        self,
        user_id: str,
        characters: int = 0,
        audio_seconds: float = 0.0,
        file_size_mb: float = 0.0,
        request_type: str = "tts",
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageStats:
        """
        Record usage for a user.
        
        Args:
            user_id: User identifier
            characters: Number of characters processed
            audio_seconds: Duration of audio generated
            file_size_mb: Size of files processed
            request_type: Type of request (tts, upload, etc.)
            metadata: Additional metadata
            
        Returns:
            Updated UsageStats
        """
        with self._lock:
            stats = self._get_or_create_stats(user_id)
            now = datetime.now(timezone.utc)
            
            # Update totals
            stats.total_requests += 1
            stats.total_characters += characters
            stats.total_audio_seconds += audio_seconds
            stats.total_file_size_mb += file_size_mb
            stats.last_request_time = now.isoformat()
            
            # Reset minute/hour/day counters if needed
            if stats.last_request_time:
                try:
                    last = datetime.fromisoformat(stats.last_request_time.replace('Z', '+00:00'))
                    
                    # Reset daily counter at midnight
                    if last.date() < now.date():
                        stats.requests_today = 0
                    
                    # Reset hourly counter
                    if (now - last).total_seconds() > 3600:
                        stats.requests_this_hour = 0
                    
                    # Reset minute counter
                    if (now - last).total_seconds() > 60:
                        stats.requests_this_minute = 0
                except:
                    pass
            
            stats.requests_today += 1
            stats.requests_this_hour += 1
            stats.requests_this_minute += 1
            
            # Record to history
            self._usage_history.append({
                'user_id': user_id,
                'timestamp': now.isoformat(),
                'request_type': request_type,
                'characters': characters,
                'audio_seconds': audio_seconds,
                'file_size_mb': file_size_mb,
                'metadata': metadata or {}
            })
            
            # Limit history size
            if len(self._usage_history) > 10000:
                self._usage_history = self._usage_history[-5000:]
            
            # Save periodically
            if stats.total_requests % 10 == 0:
                self._save_stats()
            
            return stats
    
    def get_user_stats(self, user_id: str) -> UsageStats:
        """Get usage statistics for a user."""
        with self._lock:
            return self._get_or_create_stats(user_id)
    
    def get_all_stats(self) -> Dict[str, UsageStats]:
        """Get all user statistics."""
        return dict(self._user_stats)
    
    def get_usage_summary(
        self,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get usage summary.
        
        Args:
            user_id: Optional user to filter by
            days: Number of days to include
            
        Returns:
            Usage summary dictionary
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        relevant_history = [
            h for h in self._usage_history
            if h['timestamp'] > cutoff_str and
               (user_id is None or h['user_id'] == user_id)
        ]
        
        return {
            'period_days': days,
            'total_requests': len(relevant_history),
            'total_characters': sum(h['characters'] for h in relevant_history),
            'total_audio_seconds': sum(h['audio_seconds'] for h in relevant_history),
            'total_file_size_mb': sum(h['file_size_mb'] for h in relevant_history),
            'unique_users': len(set(h['user_id'] for h in relevant_history)),
            'requests_by_type': self._count_by_key(relevant_history, 'request_type'),
            'requests_by_day': self._aggregate_by_day(relevant_history)
        }
    
    def _count_by_key(
        self, 
        history: List[Dict], 
        key: str
    ) -> Dict[str, int]:
        """Count history entries by a key."""
        counts = defaultdict(int)
        for h in history:
            counts[h.get(key, 'unknown')] += 1
        return dict(counts)
    
    def _aggregate_by_day(self, history: List[Dict]) -> Dict[str, int]:
        """Aggregate request counts by day."""
        by_day = defaultdict(int)
        for h in history:
            day = h['timestamp'][:10]  # YYYY-MM-DD
            by_day[day] += 1
        return dict(sorted(by_day.items()))
    
    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by usage."""
        sorted_users = sorted(
            self._user_stats.values(),
            key=lambda s: s.total_requests,
            reverse=True
        )[:limit]
        
        return [
            {
                'user_id': s.user_id,
                'total_requests': s.total_requests,
                'total_characters': s.total_characters,
                'total_audio_seconds': round(s.total_audio_seconds, 2),
                'tier': s.tier.value
            }
            for s in sorted_users
        ]
    
    def check_character_limit(
        self,
        user_id: str,
        characters: int
    ) -> Tuple[bool, str]:
        """
        Check if a character count is within user limits.
        
        Args:
            user_id: User identifier
            characters: Number of characters to check
            
        Returns:
            Tuple of (allowed, reason)
        """
        if not self.rate_limiter:
            return (True, "")
        
        tier = self.rate_limiter.get_user_tier(user_id)
        config = self.rate_limiter.get_tier_config(tier)
        
        if characters > config.max_characters_per_request:
            return (
                False, 
                f"Text too long. Maximum {config.max_characters_per_request} characters "
                f"for {tier.value} tier. Provided: {characters}"
            )
        
        return (True, "")
    
    def check_audio_duration_limit(
        self,
        user_id: str,
        duration_seconds: float
    ) -> Tuple[bool, str]:
        """
        Check if audio duration is within user limits.
        
        Args:
            user_id: User identifier
            duration_seconds: Audio duration to check
            
        Returns:
            Tuple of (allowed, reason)
        """
        if not self.rate_limiter:
            return (True, "")
        
        tier = self.rate_limiter.get_user_tier(user_id)
        config = self.rate_limiter.get_tier_config(tier)
        
        if duration_seconds > config.max_audio_duration_seconds:
            return (
                False,
                f"Audio too long. Maximum {config.max_audio_duration_seconds}s "
                f"for {tier.value} tier. Provided: {duration_seconds}s"
            )
        
        return (True, "")
    
    def export_usage_report(
        self,
        output_path: Optional[str] = None,
        days: int = 30
    ) -> str:
        """
        Export usage report to JSON file.
        
        Args:
            output_path: Output file path
            days: Days to include in report
            
        Returns:
            Path to exported file
        """
        if not output_path:
            output_path = self.storage_dir / f"usage_report_{datetime.now().strftime('%Y%m%d')}.json"
        else:
            output_path = Path(output_path)
        
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'period_days': days,
            'summary': self.get_usage_summary(days=days),
            'top_users': self.get_top_users(20),
            'user_stats': {
                user_id: stats.to_dict()
                for user_id, stats in self._user_stats.items()
            }
        }
        
        output_path.write_text(json.dumps(report, indent=2))
        return str(output_path)
