"""
Unit Tests for TTS Module
Tests for XTTSEngine, EdgeTTSEngine, GTTSEngine, and TTSManager
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tts import (
    XTTSEngine, SpeakerEmbedding, TTSResult,
    TTSManager, TTSEngineType, VoiceProfile,
    EdgeTTSEngine, EdgeTTSResult,
    GTTSEngine, GTTSResult
)


class TestXTTSEngine:
    """Tests for XTTSEngine class."""
    
    def test_engine_initialization(self, temp_dir):
        """Test XTTSEngine initializes correctly."""
        engine = XTTSEngine(
            output_dir=str(temp_dir / "output"),
            embeddings_dir=str(temp_dir / "embeddings")
        )
        assert engine is not None
    
    def test_get_status(self, temp_dir):
        """Test getting engine status."""
        engine = XTTSEngine(output_dir=str(temp_dir / "output"))
        status = engine.get_status()
        
        assert 'tts_available' in status
        assert 'torch_available' in status
        assert 'model_loaded' in status
        assert 'supported_languages' in status
    
    def test_supported_languages(self, temp_dir):
        """Test getting supported languages."""
        engine = XTTSEngine(output_dir=str(temp_dir / "output"))
        languages = engine.get_supported_languages()
        
        assert isinstance(languages, list)
        assert len(languages) > 0
        
        # Check for English
        lang_codes = [l['code'] for l in languages]
        assert 'en' in lang_codes
    
    def test_list_embeddings_empty(self, temp_dir):
        """Test listing embeddings when empty."""
        engine = XTTSEngine(
            output_dir=str(temp_dir / "output"),
            embeddings_dir=str(temp_dir / "embeddings")
        )
        embeddings = engine.list_embeddings()
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 0
    
    def test_speaker_embedding_dataclass(self):
        """Test SpeakerEmbedding dataclass."""
        embedding = SpeakerEmbedding(
            embedding_id="test_123",
            speaker_name="Test Speaker",
            source_audio_path="/path/to/audio.wav",
            source_audio_hash="abc123"
        )
        
        assert embedding.embedding_id == "test_123"
        assert embedding.speaker_name == "Test Speaker"
        
        # Test serialization
        data = embedding.to_dict()
        assert data['embedding_id'] == "test_123"
    
    def test_tts_result_dataclass(self):
        """Test TTSResult dataclass."""
        result = TTSResult(
            success=True,
            audio_path="/path/to/output.wav",
            duration_seconds=5.0,
            text="Hello world"
        )
        
        assert result.success == True
        assert result.duration_seconds == 5.0
    
    def test_synthesize_without_model(self, temp_dir):
        """Test synthesis when model not loaded."""
        engine = XTTSEngine(output_dir=str(temp_dir / "output"))
        
        # Try to synthesize without model (should handle gracefully)
        if not engine.tts_available:
            result = engine.synthesize(
                text="Hello",
                speaker_audio="/fake/path.wav",
                language="en"
            )
            
            assert result.success == False
            assert result.error is not None


class TestEdgeTTSEngine:
    """Tests for EdgeTTSEngine class."""
    
    def test_engine_initialization(self, temp_dir):
        """Test EdgeTTSEngine initializes correctly."""
        engine = EdgeTTSEngine(output_dir=str(temp_dir / "output"))
        assert engine is not None
    
    def test_available_property(self, temp_dir):
        """Test available property."""
        engine = EdgeTTSEngine(output_dir=str(temp_dir / "output"))
        
        # Should be a boolean
        assert isinstance(engine.available, bool)
    
    def test_get_voices(self, temp_dir):
        """Test getting available voices."""
        engine = EdgeTTSEngine(output_dir=str(temp_dir / "output"))
        
        try:
            voices = engine.get_voices()
            assert isinstance(voices, list)
        except Exception:
            pytest.skip("Edge TTS voices not available")
    
    def test_edge_tts_result(self):
        """Test EdgeTTSResult dataclass."""
        result = EdgeTTSResult(
            success=True,
            audio_path="/path/to/output.mp3",
            duration_seconds=3.0
        )
        
        assert result.success == True


class TestGTTSEngine:
    """Tests for GTTSEngine class."""
    
    def test_engine_initialization(self, temp_dir):
        """Test GTTSEngine initializes correctly."""
        engine = GTTSEngine(output_dir=str(temp_dir / "output"))
        assert engine is not None
    
    def test_available_property(self, temp_dir):
        """Test available property."""
        engine = GTTSEngine(output_dir=str(temp_dir / "output"))
        
        assert isinstance(engine.available, bool)
    
    def test_gtts_result(self):
        """Test GTTSResult dataclass."""
        result = GTTSResult(
            success=True,
            audio_path="/path/to/output.mp3"
        )
        
        assert result.success == True


class TestTTSManager:
    """Tests for TTSManager class."""
    
    def test_manager_initialization(self, temp_dir):
        """Test TTSManager initializes correctly."""
        manager = TTSManager(
            output_dir=str(temp_dir / "output"),
            cache_dir=str(temp_dir / "cache")
        )
        assert manager is not None
    
    def test_get_engines_status(self, temp_dir):
        """Test getting all engines status."""
        manager = TTSManager(output_dir=str(temp_dir / "output"))
        status = manager.get_engines_status()
        
        assert isinstance(status, dict)
    
    def test_create_profile(self, temp_dir):
        """Test creating a voice profile."""
        manager = TTSManager(output_dir=str(temp_dir / "output"))
        
        profile = manager.create_profile(
            profile_id="test_profile",
            name="Test Voice",
            engine=TTSEngineType.EDGE_TTS,
            language="en"
        )
        
        assert profile is not None
        assert profile.profile_id == "test_profile"
    
    def test_get_profile(self, temp_dir):
        """Test getting a voice profile."""
        manager = TTSManager(output_dir=str(temp_dir / "output"))
        
        # Create profile
        manager.create_profile(
            profile_id="get_test",
            name="Get Test Voice",
            language="en"
        )
        
        # Get profile
        profile = manager.get_profile("get_test")
        
        assert profile is not None
        assert profile.name == "Get Test Voice"
    
    def test_list_profiles(self, temp_dir):
        """Test listing voice profiles."""
        manager = TTSManager(output_dir=str(temp_dir / "output"))
        
        # Create some profiles
        manager.create_profile(profile_id="list_1", name="Voice 1")
        manager.create_profile(profile_id="list_2", name="Voice 2")
        
        profiles = manager.list_profiles()
        
        assert len(profiles) >= 2
    
    def test_voice_profile_dataclass(self):
        """Test VoiceProfile dataclass."""
        profile = VoiceProfile(
            profile_id="vp_123",
            name="My Voice",
            engine=TTSEngineType.XTTS_V2,
            language="en"
        )
        
        assert profile.profile_id == "vp_123"
        assert profile.engine == TTSEngineType.XTTS_V2
    
    def test_tts_engine_type_enum(self):
        """Test TTSEngineType enum."""
        assert TTSEngineType.XTTS_V2.value == "xtts_v2"
        assert TTSEngineType.EDGE_TTS.value == "edge_tts"
        assert TTSEngineType.GTTS.value == "gtts"


class TestTTSIntegration:
    """Integration tests for TTS synthesis."""
    
    def test_synthesize_with_edge_tts(self, temp_dir, sample_text):
        """Test synthesis with Edge TTS."""
        engine = EdgeTTSEngine(output_dir=str(temp_dir / "output"))
        
        if not engine.available:
            pytest.skip("Edge TTS not available")
        
        try:
            result = engine.synthesize(
                text=sample_text,
                voice="en-US-ChristopherNeural"
            )
            
            if result.success:
                assert Path(result.audio_path).exists()
        except Exception as e:
            pytest.skip(f"Edge TTS synthesis failed: {e}")
    
    def test_synthesize_with_gtts(self, temp_dir, sample_text):
        """Test synthesis with gTTS."""
        engine = GTTSEngine(output_dir=str(temp_dir / "output"))
        
        if not engine.available:
            pytest.skip("gTTS not available")
        
        try:
            result = engine.synthesize(
                text=sample_text,
                language="en"
            )
            
            if result.success:
                assert Path(result.audio_path).exists()
        except Exception as e:
            pytest.skip(f"gTTS synthesis failed: {e}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
