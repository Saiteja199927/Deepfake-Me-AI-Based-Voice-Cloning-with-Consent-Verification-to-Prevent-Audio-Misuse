"""
TTS Engine Module
Provides text-to-speech functionality using multiple backends
"""

class TTSEngine:
    """Base TTS Engine class"""
    
    def __init__(self):
        self.engine_type = None
    
    def speak(self, text: str) -> None:
        """Convert text to speech and play"""
        raise NotImplementedError
    
    def save(self, text: str, output_path: str) -> str:
        """Convert text to speech and save to file"""
        raise NotImplementedError
