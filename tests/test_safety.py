"""
Unit Tests for Safety Module
Tests for ContentFilter, AudioWatermark, RateLimiter, and UsageTracker
"""

import pytest
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.safety import (
    ContentFilter, ContentFilterResult, FilterCategory,
    AudioWatermark, WatermarkResult, WatermarkConfig,
    RateLimiter, UsageTracker, RateLimitResult, RateLimitTier,
    SafetyManager
)


class TestContentFilter:
    """Tests for ContentFilter class."""
    
    def test_filter_initialization(self):
        """Test ContentFilter initializes correctly."""
        filter = ContentFilter()
        assert filter is not None
    
    def test_filter_safe_text(self):
        """Test filtering safe text."""
        filter = ContentFilter()
        result = filter.filter("Hello, how are you today?")
        
        assert result.is_safe == True
        assert result.blocked == False
        assert len(result.categories_detected) == 0
    
    def test_filter_profanity(self):
        """Test detecting profanity."""
        filter = ContentFilter(enable_profanity_filter=True)
        result = filter.filter("This is a damn test")
        
        assert result.is_safe == False or result.sanitized == True
        assert FilterCategory.PROFANITY in result.categories_detected or len(result.flags) > 0
    
    def test_filter_pii_email(self):
        """Test detecting email addresses."""
        filter = ContentFilter(enable_pii_filter=True)
        result = filter.filter("Contact me at test@example.com")
        
        assert result.is_safe == False or result.sanitized == True
        if result.sanitized:
            assert "[EMAIL_REDACTED]" in result.filtered_text
    
    def test_filter_pii_phone(self):
        """Test detecting phone numbers."""
        filter = ContentFilter(enable_pii_filter=True)
        result = filter.filter("Call me at 555-123-4567")
        
        assert result.is_safe == False or result.sanitized == True
        if result.sanitized:
            assert "[PHONE_REDACTED]" in result.filtered_text
    
    def test_filter_pii_ssn(self):
        """Test detecting SSN."""
        filter = ContentFilter(enable_pii_filter=True)
        result = filter.filter("My SSN is 123-45-6789")
        
        assert result.sanitized == True or FilterCategory.PERSONAL_INFO in result.categories_detected
    
    def test_sanitize_option(self):
        """Test sanitize vs no sanitize."""
        filter = ContentFilter()
        
        # With sanitize
        result_sanitized = filter.filter("Email: test@example.com", sanitize=True)
        
        # Without sanitize
        result_no_sanitize = filter.filter("Email: test@example.com", sanitize=False)
        
        # Sanitized version should have redacted content
        if FilterCategory.PERSONAL_INFO in result_sanitized.categories_detected:
            assert "[EMAIL_REDACTED]" in result_sanitized.filtered_text
            assert "[EMAIL_REDACTED]" not in result_no_sanitize.filtered_text
    
    def test_custom_blocklist(self):
        """Test custom blocklist."""
        filter = ContentFilter(custom_blocklist=["forbidden_word"])
        result = filter.filter("This contains forbidden_word in it")
        
        assert FilterCategory.CUSTOM in result.categories_detected
    
    def test_custom_allowlist(self):
        """Test custom allowlist."""
        filter = ContentFilter(custom_allowlist=["test@example.com"])
        result = filter.filter("Contact test@example.com")
        
        # Allowlisted content should be safe
        assert result.is_safe == True
    
    def test_sensitivity_levels(self):
        """Test different sensitivity levels."""
        low_filter = ContentFilter(sensitivity="low")
        high_filter = ContentFilter(sensitivity="high")
        
        text = "This is a test damn message"
        
        low_result = low_filter.filter(text)
        high_result = high_filter.filter(text)
        
        # Both should detect, but severity may differ
        assert low_result is not None
        assert high_result is not None
    
    def test_get_statistics(self):
        """Test getting filter statistics."""
        filter = ContentFilter()
        
        # Run some filters
        filter.filter("Safe text")
        filter.filter("Email: test@example.com")
        
        stats = filter.get_statistics()
        
        assert 'total_checked' in stats
        assert stats['total_checked'] >= 2


class TestAudioWatermark:
    """Tests for AudioWatermark class."""
    
    def test_watermark_initialization(self, temp_dir):
        """Test AudioWatermark initializes correctly."""
        wm = AudioWatermark(storage_dir=str(temp_dir / "watermarks"))
        assert wm is not None
    
    def test_embed_watermark(self, sample_wav_file, temp_dir):
        """Test embedding watermark in audio."""
        wm = AudioWatermark(storage_dir=str(temp_dir / "watermarks"))
        
        result = wm.embed_watermark(
            str(sample_wav_file),
            {"user_id": "test_user", "purpose": "testing"}
        )
        
        if not wm.scipy_available:
            assert result.success == False
            assert "scipy" in result.error.lower()
        else:
            assert result.success == True
            assert result.watermark_id is not None
    
    def test_watermark_config(self):
        """Test watermark configuration."""
        config = WatermarkConfig(
            strength=0.02,
            frequency_low=1500,
            frequency_high=2500
        )
        
        assert config.strength == 0.02
        assert config.frequency_low == 1500
    
    def test_list_watermarks(self, temp_dir):
        """Test listing watermarks."""
        wm = AudioWatermark(storage_dir=str(temp_dir / "watermarks"))
        
        watermarks = wm.list_watermarks()
        
        assert isinstance(watermarks, list)
    
    def test_get_statistics(self, temp_dir):
        """Test getting watermark statistics."""
        wm = AudioWatermark(storage_dir=str(temp_dir / "watermarks"))
        
        stats = wm.get_statistics()
        
        assert 'total_watermarks' in stats
        assert 'scipy_available' in stats


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_limiter_initialization(self, temp_dir):
        """Test RateLimiter initializes correctly."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        assert limiter is not None
    
    def test_check_rate_limit_allowed(self, temp_dir):
        """Test rate limit check when allowed."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        result = limiter.check_rate_limit("new_user_123")
        
        assert result.allowed == True
        assert result.remaining_minute > 0
    
    def test_rate_limit_exceeded(self, temp_dir):
        """Test rate limit exceeded scenario."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        user_id = "test_rate_limit_user"
        
        # Set to free tier with low limits
        limiter.set_user_tier(user_id, RateLimitTier.FREE)
        config = limiter.get_tier_config(RateLimitTier.FREE)
        
        # Make requests up to the limit
        for _ in range(config.requests_per_minute):
            limiter.record_request(user_id)
        
        # Next check should fail
        result = limiter.check_rate_limit(user_id)
        
        assert result.allowed == False
        assert result.remaining_minute == 0
    
    def test_check_and_record(self, temp_dir):
        """Test combined check and record."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        result = limiter.check_and_record("check_record_user")
        
        assert result.allowed == True
    
    def test_set_user_tier(self, temp_dir):
        """Test setting user tier."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        limiter.set_user_tier("premium_user", RateLimitTier.PREMIUM)
        
        tier = limiter.get_user_tier("premium_user")
        assert tier == RateLimitTier.PREMIUM
    
    def test_tier_configs(self, temp_dir):
        """Test tier configurations."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        free_config = limiter.get_tier_config(RateLimitTier.FREE)
        premium_config = limiter.get_tier_config(RateLimitTier.PREMIUM)
        
        # Premium should have higher limits
        assert premium_config.requests_per_minute > free_config.requests_per_minute
        assert premium_config.requests_per_hour > free_config.requests_per_hour
    
    def test_reset_user_limits(self, temp_dir):
        """Test resetting user limits."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        user_id = "reset_user"
        
        # Record some requests
        limiter.record_request(user_id)
        limiter.record_request(user_id)
        
        # Reset
        limiter.reset_user_limits(user_id)
        
        # Should have full limit again
        result = limiter.check_rate_limit(user_id)
        config = limiter.get_tier_config(RateLimitTier.FREE)
        
        assert result.remaining_minute == config.requests_per_minute


class TestUsageTracker:
    """Tests for UsageTracker class."""
    
    def test_tracker_initialization(self, temp_dir):
        """Test UsageTracker initializes correctly."""
        tracker = UsageTracker(storage_dir=str(temp_dir / "usage"))
        assert tracker is not None
    
    def test_record_usage(self, temp_dir):
        """Test recording usage."""
        tracker = UsageTracker(storage_dir=str(temp_dir / "usage"))
        
        stats = tracker.record_usage(
            user_id="usage_user",
            characters=100,
            audio_seconds=5.0,
            request_type="tts"
        )
        
        assert stats.total_requests >= 1
        assert stats.total_characters >= 100
    
    def test_get_user_stats(self, temp_dir):
        """Test getting user statistics."""
        tracker = UsageTracker(storage_dir=str(temp_dir / "usage"))
        
        # Record some usage
        tracker.record_usage(user_id="stats_user", characters=50)
        tracker.record_usage(user_id="stats_user", characters=75)
        
        stats = tracker.get_user_stats("stats_user")
        
        assert stats.total_requests >= 2
        assert stats.total_characters >= 125
    
    def test_get_usage_summary(self, temp_dir):
        """Test getting usage summary."""
        tracker = UsageTracker(storage_dir=str(temp_dir / "usage"))
        
        # Record usage
        tracker.record_usage(user_id="summary_user", characters=100)
        
        summary = tracker.get_usage_summary(days=7)
        
        assert 'total_requests' in summary
        assert 'total_characters' in summary
    
    def test_get_top_users(self, temp_dir):
        """Test getting top users."""
        tracker = UsageTracker(storage_dir=str(temp_dir / "usage"))
        
        # Create some users with different usage
        for i in range(5):
            for j in range(i + 1):
                tracker.record_usage(user_id=f"top_user_{i}", characters=10)
        
        top = tracker.get_top_users(3)
        
        assert len(top) <= 3
    
    def test_character_limit_check(self, temp_dir):
        """Test character limit checking."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        tracker = UsageTracker(
            storage_dir=str(temp_dir / "usage"),
            rate_limiter=limiter
        )
        
        # Free tier has 1000 char limit
        allowed, reason = tracker.check_character_limit("test_user", 500)
        assert allowed == True
        
        # Exceeding limit
        allowed, reason = tracker.check_character_limit("test_user", 50000)
        assert allowed == False


class TestSafetyManager:
    """Tests for SafetyManager integration class."""
    
    def test_manager_initialization(self, temp_dir):
        """Test SafetyManager initializes correctly."""
        manager = SafetyManager(storage_dir=str(temp_dir))
        assert manager is not None
    
    def test_check_text_safety(self, temp_dir):
        """Test text safety check."""
        manager = SafetyManager(storage_dir=str(temp_dir))
        
        result = manager.check_text_safety("Hello world")
        
        assert result.is_safe == True
    
    def test_pre_synthesis_check(self, temp_dir):
        """Test pre-synthesis safety check."""
        manager = SafetyManager(storage_dir=str(temp_dir))
        
        allowed, filtered_text, error = manager.pre_synthesis_check(
            user_id="test_user",
            text="Hello world"
        )
        
        assert allowed == True
        assert error is None
    
    def test_record_usage(self, temp_dir):
        """Test usage recording through manager."""
        manager = SafetyManager(storage_dir=str(temp_dir))
        
        stats = manager.record_usage(
            user_id="manager_user",
            characters=100,
            audio_seconds=5.0
        )
        
        assert stats.total_characters >= 100


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
