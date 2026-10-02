"""
Helper Utilities
Common utility functions used across the application
"""

import os
from pathlib import Path


def ensure_dir(directory: str) -> Path:
    """Ensure directory exists, create if not"""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower().lstrip('.')


def is_valid_audio_file(filename: str) -> bool:
    """Check if file is a valid audio format"""
    valid_extensions = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}
    return get_file_extension(filename) in valid_extensions
