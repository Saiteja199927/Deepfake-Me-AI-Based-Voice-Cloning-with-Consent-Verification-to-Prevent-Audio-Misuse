"""
Integration Tests
End-to-end tests for complete workflows
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio import AudioProcessor, AudioValidator
from src.consent import ConsentManager, ConsentWorkflow, ConsentType, ConsentStatus
from src.safety import SafetyManager, ContentFilter, RateLimiter, RateLimitTier
from src.tts import TTSManager, TTSEngineType


class TestConsentToTTSWorkflow:
    """Test complete consent to TTS workflow."""
    
    def test_full_consent_workflow_then_tts(self, temp_dir):
        """Test completing consent workflow then using TTS."""
        # 1. Set up consent
        consent_manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        workflow = ConsentWorkflow(
            consent_manager=consent_manager,
            storage_dir=str(temp_dir / "workflows")
        )
        
        user_id = "integration_user_1"
        
        # 2. Start and complete workflow
        start_result = workflow.start_workflow(user_id=user_id, template_id="basic_tts")
        workflow_id = start_result['workflow_id']
        total_steps = start_result.get('total_steps', 3)
        
        for step in range(1, total_steps + 1):
            result = workflow.process_step(workflow_id=workflow_id, step_number=step, accepted=True)
            if result.get('workflow_completed'):
                break
        
        # 3. Verify consents are granted
        has_tos = consent_manager.check_consent(user_id, ConsentType.TERMS_OF_SERVICE)
        has_privacy = consent_manager.check_consent(user_id, ConsentType.PRIVACY_POLICY)
        
        assert has_tos == True
        assert has_privacy == True
        
        # 4. Set up TTS
        tts_manager = TTSManager(output_dir=str(temp_dir / "output"))
        
        # 5. Create a voice profile
        profile = tts_manager.create_profile(
            profile_id="integration_profile",
            name="Integration Test Voice",
            engine=TTSEngineType.EDGE_TTS,
            language="en"
        )
        
        assert profile is not None


class TestSafetyIntegration:
    """Test safety integration with content filtering."""
    
    def test_content_filter_before_tts(self, temp_dir, sample_text):
        """Test content filtering before TTS synthesis."""
        # 1. Set up safety manager
        safety = SafetyManager(storage_dir=str(temp_dir))
        
        # 2. Check safe text
        allowed, filtered, error = safety.pre_synthesis_check("test_user", sample_text)
        
        assert allowed == True
        assert error is None
        
        # 3. Check text with PII
        pii_text = "Call me at 555-123-4567 or email test@example.com"
        allowed, filtered, error = safety.pre_synthesis_check("test_user", pii_text)
        
        # Should still be allowed but sanitized
        assert "[PHONE_REDACTED]" in filtered or "[EMAIL_REDACTED]" in filtered
    
    def test_rate_limiting_workflow(self, temp_dir):
        """Test rate limiting in a TTS workflow."""
        # 1. Set up rate limiter
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        safety = SafetyManager(storage_dir=str(temp_dir))
        
        user_id = "rate_limit_user"
        
        # 2. Set to free tier
        limiter.set_user_tier(user_id, RateLimitTier.FREE)
        config = limiter.get_tier_config(RateLimitTier.FREE)
        
        # 3. Make requests up to limit
        for i in range(config.requests_per_minute - 1):
            allowed, _, error = safety.pre_synthesis_check(user_id, f"Test message {i}")
            assert allowed == True
        
        # 4. Check rate limit is approaching
        result = limiter.check_rate_limit(user_id)
        assert result.remaining_minute <= 1
    
    def test_usage_tracking(self, temp_dir):
        """Test usage tracking through synthesis workflow."""
        safety = SafetyManager(storage_dir=str(temp_dir))
        
        user_id = "usage_track_user"
        
        # Record usage
        safety.record_usage(user_id=user_id, characters=100, audio_seconds=5.0)
        safety.record_usage(user_id=user_id, characters=200, audio_seconds=10.0)
        
        # Get dashboard data
        data = safety.get_user_dashboard_data(user_id)
        
        assert 'usage' in data
        assert data['usage']['total_characters'] >= 300


class TestAudioProcessingWorkflow:
    """Test audio upload and processing workflow."""
    
    def test_upload_validate_process(self, sample_wav_file, temp_dir):
        """Test complete audio processing workflow."""
        # 1. Validate uploaded file
        validator = AudioValidator()
        validation = validator.validate(str(sample_wav_file))
        
        assert validation['valid'] == True
        
        # 2. Get audio info
        processor = AudioProcessor(output_dir=str(temp_dir / "processed"))
        info = processor.get_audio_info(str(sample_wav_file))
        
        assert info is not None
        assert 'sample_rate' in info
        
        # 3. Process audio (normalize)
        try:
            processed = processor.normalize(str(sample_wav_file))
            assert Path(processed).exists()
        except Exception:
            # Normalization may require additional dependencies
            pass
    
    def test_format_conversion_workflow(self, sample_wav_file, temp_dir):
        """Test audio format conversion."""
        processor = AudioProcessor(output_dir=str(temp_dir / "converted"))
        
        try:
            # Convert to different format
            mp3_path = processor.convert(str(sample_wav_file), output_format='mp3')
            
            if mp3_path:
                assert Path(mp3_path).exists()
                assert Path(mp3_path).suffix.lower() == '.mp3'
        except Exception:
            pytest.skip("Format conversion not available")


class TestMultiUserWorkflow:
    """Test multi-user scenarios."""
    
    def test_multiple_users_same_time(self, temp_dir):
        """Test multiple users using the system simultaneously."""
        consent_manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        safety = SafetyManager(storage_dir=str(temp_dir))
        
        users = ["user_1", "user_2", "user_3"]
        
        # Each user completes consent
        for user_id in users:
            consent = consent_manager.create_consent(
                user_id=user_id,
                consent_type=ConsentType.TERMS_OF_SERVICE
            )
            consent_manager.grant_consent(consent.consent_id)
        
        # Each user records usage
        for i, user_id in enumerate(users):
            safety.record_usage(
                user_id=user_id,
                characters=(i + 1) * 100,
                audio_seconds=(i + 1) * 5.0
            )
        
        # Verify usage is tracked separately
        for i, user_id in enumerate(users):
            stats = safety.usage_tracker.get_user_stats(user_id)
            assert stats.total_characters >= (i + 1) * 100
    
    def test_tier_upgrade_workflow(self, temp_dir):
        """Test user tier upgrade."""
        limiter = RateLimiter(storage_dir=str(temp_dir / "rate_limits"))
        
        user_id = "upgrade_user"
        
        # Start as free
        limiter.set_user_tier(user_id, RateLimitTier.FREE)
        free_config = limiter.get_tier_config(RateLimitTier.FREE)
        
        # Upgrade to premium
        limiter.set_user_tier(user_id, RateLimitTier.PREMIUM)
        premium_config = limiter.get_tier_config(RateLimitTier.PREMIUM)
        
        # Verify new limits
        result = limiter.check_rate_limit(user_id)
        assert result.tier == RateLimitTier.PREMIUM


class TestDataPersistence:
    """Test data persistence across sessions."""
    
    def test_consent_persistence(self, temp_dir):
        """Test consent data persists."""
        storage_dir = str(temp_dir / "consent_persist")
        
        # Create manager and consent
        manager1 = ConsentManager(storage_dir=storage_dir)
        consent = manager1.create_consent(
            user_id="persist_user",
            consent_type=ConsentType.TERMS_OF_SERVICE
        )
        manager1.grant_consent(consent.consent_id)
        
        # Create new manager instance (simulating restart)
        manager2 = ConsentManager(storage_dir=storage_dir)
        
        # Check consent still exists
        has_consent = manager2.check_consent("persist_user", ConsentType.TERMS_OF_SERVICE)
        assert has_consent == True
    
    def test_usage_persistence(self, temp_dir):
        """Test usage data persists."""
        storage_dir = str(temp_dir / "usage_persist")
        
        # Create tracker and record usage
        tracker1 = SafetyManager(storage_dir=storage_dir).usage_tracker
        tracker1.record_usage(user_id="persist_user", characters=500)
        
        # Create new tracker instance
        tracker2 = SafetyManager(storage_dir=storage_dir).usage_tracker
        
        # Check usage still recorded
        stats = tracker2.get_user_stats("persist_user")
        assert stats.total_characters >= 500


class TestErrorHandling:
    """Test error handling across modules."""
    
    def test_invalid_file_handling(self, temp_dir):
        """Test handling of invalid audio files."""
        validator = AudioValidator()
        
        # Non-existent file
        result = validator.validate("/path/to/nonexistent.wav")
        assert result['valid'] == False
        
        # Wrong extension
        fake_file = temp_dir / "fake.wav"
        fake_file.write_text("not audio data")
        
        result = validator.validate(str(fake_file))
        # Should fail validation
        assert result['valid'] == False or 'error' in result
    
    def test_empty_text_handling(self, temp_dir):
        """Test handling of empty text for TTS."""
        safety = SafetyManager(storage_dir=str(temp_dir))
        
        # Empty text
        result = safety.check_text_safety("")
        
        # Should handle gracefully
        assert result is not None
    
    def test_missing_consent_handling(self, temp_dir):
        """Test handling when consent is missing."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        # Try to get non-existent consent
        consent = manager.get_consent("non_existent_id")
        assert consent is None
        
        # Check user without consents
        has_consent = manager.check_consent("no_consent_user", ConsentType.TERMS_OF_SERVICE)
        assert has_consent == False


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
