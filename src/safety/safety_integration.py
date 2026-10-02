"""
Safety Integration Module
Integrates all safety features for easy use in Streamlit pages
"""

import streamlit as st
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from .content_filter import ContentFilter, ContentFilterResult, FilterCategory
from .audio_watermark import AudioWatermark, WatermarkResult, WatermarkConfig
from .rate_limiter import RateLimiter, UsageTracker, RateLimitResult, RateLimitTier, UsageStats


class SafetyManager:
    """
    Unified safety manager for TTS applications.
    
    Combines:
    - Content filtering
    - Audio watermarking
    - Rate limiting
    - Usage tracking
    """
    
    def __init__(
        self,
        storage_dir: Optional[str] = None,
        enable_content_filter: bool = True,
        enable_watermarking: bool = True,
        enable_rate_limiting: bool = True,
        filter_sensitivity: str = "medium"
    ):
        """
        Initialize Safety Manager.
        
        Args:
            storage_dir: Base directory for all safety data
            enable_content_filter: Enable content filtering
            enable_watermarking: Enable audio watermarking
            enable_rate_limiting: Enable rate limiting
            filter_sensitivity: Content filter sensitivity level
        """
        base_dir = Path(storage_dir) if storage_dir else Path("data")
        
        # Initialize components
        self.content_filter = ContentFilter(
            sensitivity=filter_sensitivity
        ) if enable_content_filter else None
        
        self.watermark = AudioWatermark(
            storage_dir=str(base_dir / "watermarks")
        ) if enable_watermarking else None
        
        self.rate_limiter = RateLimiter(
            storage_dir=str(base_dir / "rate_limits")
        ) if enable_rate_limiting else None
        
        self.usage_tracker = UsageTracker(
            storage_dir=str(base_dir / "usage"),
            rate_limiter=self.rate_limiter
        )
        
        # Configuration
        self.enable_content_filter = enable_content_filter
        self.enable_watermarking = enable_watermarking
        self.enable_rate_limiting = enable_rate_limiting
    
    def check_text_safety(self, text: str, sanitize: bool = True) -> ContentFilterResult:
        """
        Check if text is safe for TTS synthesis.
        
        Args:
            text: Text to check
            sanitize: Whether to sanitize flagged content
            
        Returns:
            ContentFilterResult
        """
        if not self.content_filter:
            return ContentFilterResult(
                is_safe=True,
                original_text=text,
                filtered_text=text
            )
        
        return self.content_filter.filter(text, sanitize=sanitize)
    
    def check_rate_limit(self, user_id: str) -> RateLimitResult:
        """
        Check if user can make a request.
        
        Args:
            user_id: User identifier
            
        Returns:
            RateLimitResult
        """
        if not self.rate_limiter:
            return RateLimitResult(
                allowed=True,
                user_id=user_id,
                tier=RateLimitTier.UNLIMITED
            )
        
        return self.rate_limiter.check_and_record(user_id)
    
    def watermark_audio(
        self,
        audio_path: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WatermarkResult:
        """
        Add watermark to generated audio.
        
        Args:
            audio_path: Path to audio file
            user_id: User who generated the audio
            metadata: Additional metadata to embed
            
        Returns:
            WatermarkResult
        """
        if not self.watermark:
            return WatermarkResult(
                success=True,
                input_path=audio_path,
                output_path=audio_path,
                metadata={'watermarking_disabled': True}
            )
        
        watermark_data = {
            'user_id': user_id,
            'generated_by': 'voice_tts_studio',
            **(metadata or {})
        }
        
        return self.watermark.embed_watermark(audio_path, watermark_data)
    
    def record_usage(
        self,
        user_id: str,
        characters: int = 0,
        audio_seconds: float = 0.0,
        request_type: str = "tts"
    ) -> UsageStats:
        """
        Record usage for a user.
        
        Args:
            user_id: User identifier
            characters: Characters processed
            audio_seconds: Audio duration generated
            request_type: Type of request
            
        Returns:
            Updated UsageStats
        """
        return self.usage_tracker.record_usage(
            user_id=user_id,
            characters=characters,
            audio_seconds=audio_seconds,
            request_type=request_type
        )
    
    def pre_synthesis_check(
        self,
        user_id: str,
        text: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Perform all pre-synthesis safety checks.
        
        Args:
            user_id: User identifier
            text: Text to synthesize
            
        Returns:
            Tuple of (allowed, filtered_text, error_message)
        """
        # Check rate limit
        rate_result = self.check_rate_limit(user_id)
        if not rate_result.allowed:
            return (False, text, f"Rate limit exceeded. Try again in {rate_result.reset_time_seconds}s")
        
        # Check character limit
        allowed, reason = self.usage_tracker.check_character_limit(user_id, len(text))
        if not allowed:
            return (False, text, reason)
        
        # Check content safety
        filter_result = self.check_text_safety(text)
        if filter_result.blocked:
            return (False, text, f"Content blocked: {', '.join(c.value for c in filter_result.categories_detected)}")
        
        return (True, filter_result.filtered_text, None)
    
    def post_synthesis_process(
        self,
        user_id: str,
        audio_path: str,
        text: str,
        duration_seconds: float
    ) -> Dict[str, Any]:
        """
        Perform post-synthesis processing.
        
        Args:
            user_id: User identifier
            audio_path: Path to generated audio
            text: Original text
            duration_seconds: Audio duration
            
        Returns:
            Dictionary with processing results
        """
        results = {}
        
        # Record usage
        self.record_usage(
            user_id=user_id,
            characters=len(text),
            audio_seconds=duration_seconds,
            request_type='tts'
        )
        results['usage_recorded'] = True
        
        # Add watermark
        if self.enable_watermarking:
            wm_result = self.watermark_audio(audio_path, user_id)
            results['watermark'] = wm_result.to_dict()
        
        return results
    
    def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get safety dashboard data for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dashboard data dictionary
        """
        data = {
            'user_id': user_id
        }
        
        # Rate limit status
        if self.rate_limiter:
            rate_status = self.rate_limiter.check_rate_limit(user_id)
            tier = self.rate_limiter.get_user_tier(user_id)
            config = self.rate_limiter.get_tier_config(tier)
            
            data['rate_limit'] = {
                'tier': tier.value,
                'remaining_minute': rate_status.remaining_minute,
                'remaining_hour': rate_status.remaining_hour,
                'remaining_day': rate_status.remaining_day,
                'limits': {
                    'per_minute': config.requests_per_minute,
                    'per_hour': config.requests_per_hour,
                    'per_day': config.requests_per_day,
                    'max_characters': config.max_characters_per_request
                }
            }
        
        # Usage stats
        usage = self.usage_tracker.get_user_stats(user_id)
        data['usage'] = usage.to_dict()
        
        # Filter stats
        if self.content_filter:
            data['filter_stats'] = self.content_filter.get_statistics()
        
        return data


def render_safety_sidebar(safety_manager: SafetyManager, user_id: Optional[str]) -> None:
    """
    Render safety information in Streamlit sidebar.
    
    Args:
        safety_manager: SafetyManager instance
        user_id: Current user ID
    """
    with st.sidebar:
        st.markdown("---")
        st.subheader("🛡️ Safety Status")
        
        if not user_id:
            st.caption("Set user ID to see usage limits")
            return
        
        data = safety_manager.get_user_dashboard_data(user_id)
        
        # Rate limit info
        if 'rate_limit' in data:
            rl = data['rate_limit']
            tier = rl['tier'].upper()
            
            st.markdown(f"**Tier:** `{tier}`")
            
            # Show remaining requests
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Remaining/min", rl['remaining_minute'])
            with col2:
                st.metric("Remaining/hr", rl['remaining_hour'])
        
        # Usage info
        if 'usage' in data:
            usage = data['usage']
            st.caption(f"Total requests: {usage['total_requests']}")
            st.caption(f"Characters: {usage['total_characters']:,}")


def render_content_filter_warning(result: ContentFilterResult) -> bool:
    """
    Render content filter warning in Streamlit.
    
    Args:
        result: ContentFilterResult to display
        
    Returns:
        True if user should proceed, False if blocked
    """
    if result.is_safe:
        return True
    
    if result.blocked:
        st.error(f"""
        ⛔ **Content Blocked**
        
        Your text contains prohibited content:
        - Categories: {', '.join(c.value.replace('_', ' ').title() for c in result.categories_detected)}
        - Severity: {result.severity.value.upper()}
        
        Please revise your text and try again.
        """)
        return False
    
    if result.sanitized:
        st.warning(f"""
        ⚠️ **Content Modified**
        
        Some content was automatically sanitized:
        - Categories detected: {', '.join(c.value.replace('_', ' ').title() for c in result.categories_detected)}
        
        Original: `{result.original_text[:100]}...`
        
        Sanitized: `{result.filtered_text[:100]}...`
        """)
        
        if result.requires_review:
            return st.checkbox("I confirm this content is appropriate", value=False)
        
        return True
    
    if result.requires_review:
        st.warning(f"""
        ⚠️ **Content Requires Review**
        
        Your text may contain sensitive content:
        - Categories: {', '.join(c.value.replace('_', ' ').title() for c in result.categories_detected)}
        """)
        return st.checkbox("I confirm this content is appropriate", value=False)
    
    return True


def render_rate_limit_error(result: RateLimitResult) -> None:
    """Render rate limit error in Streamlit."""
    st.error(f"""
    ⏱️ **Rate Limit Exceeded**
    
    {result.reason}
    
    - Your tier: **{result.tier.value.upper()}**
    - Reset in: **{result.reset_time_seconds} seconds**
    
    Upgrade your tier for higher limits.
    """)
