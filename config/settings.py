"""
Application Settings
Central configuration for the TTS application
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# TTS Settings
DEFAULT_TTS_ENGINE = os.getenv("DEFAULT_TTS_ENGINE", "gtts")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
DEFAULT_VOICE_SPEED = float(os.getenv("DEFAULT_VOICE_SPEED", "1.0"))

# Audio Settings
DEFAULT_AUDIO_FORMAT = os.getenv("DEFAULT_AUDIO_FORMAT", "mp3")
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "22050"))

# Streamlit Settings
STREAMLIT_THEME = os.getenv("STREAMLIT_THEME", "dark")
