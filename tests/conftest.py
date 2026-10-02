"""
Shared test fixtures and configuration
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="voice_tts_test_")
    yield Path(temp_dir)
    # Cleanup after all tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for a single test."""
    temp_dir = tempfile.mkdtemp(prefix="voice_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_wav_file(temp_dir):
    """Create a simple WAV file for testing."""
    import wave
    import struct
    
    wav_path = temp_dir / "test_audio.wav"
    
    # Create a simple sine wave
    sample_rate = 16000
    duration = 1.0  # seconds
    frequency = 440  # Hz
    
    num_samples = int(sample_rate * duration)
    
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        import math
        for i in range(num_samples):
            sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wav_file.writeframes(struct.pack('<h', sample))
    
    return wav_path


@pytest.fixture
def sample_text():
    """Sample text for TTS testing."""
    return "Hello, this is a test of the text-to-speech system."


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"


@pytest.fixture
def mock_consent_data():
    """Mock consent data for testing."""
    return {
        'user_id': 'test_user_123',
        'consent_types': ['terms_of_service', 'privacy_policy'],
        'ip_address': '127.0.0.1',
        'user_agent': 'TestAgent/1.0'
    }


@pytest.fixture
def sample_harmful_texts():
    """Sample texts for content filter testing."""
    return {
        'safe': "Hello, how are you today?",
        'profanity': "This is a damn test",
        'pii_email': "Contact me at test@example.com",
        'pii_phone': "Call me at 555-123-4567",
        'violence': "I want to kill this bug in my code",
        'clean': "The weather is nice today."
    }
