"""
gTTS Engine
Google Text-to-Speech wrapper
"""

from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

GTTS_AVAILABLE = False
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    pass


@dataclass
class GTTSResult:
    success: bool
    audio_path: Optional[str] = None
    text: str = ""
    language: str = "en"
    error: Optional[str] = None


class GTTSEngine:
    """Google Text-to-Speech engine using gTTS library."""
    
    LANGUAGES = {
        "en": "English", "es": "Spanish", "fr": "French",
        "de": "German", "it": "Italian", "pt": "Portuguese",
        "hi": "Hindi", "ja": "Japanese", "ko": "Korean",
        "zh-CN": "Chinese", "ar": "Arabic", "ru": "Russian"
    }
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output/tts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.available = GTTS_AVAILABLE
    
    def synthesize(
        self,
        text: str,
        language: str = "en",
        output_path: Optional[str] = None,
        slow: bool = False
    ) -> GTTSResult:
        """Synthesize speech using gTTS."""
        if not self.available:
            return GTTSResult(success=False, error="gTTS not available")
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"gtts_{timestamp}.mp3"
        
        try:
            tts = gTTS(text=text, lang=language, slow=slow)
            tts.save(str(output_path))
            
            return GTTSResult(
                success=True,
                audio_path=str(output_path),
                text=text,
                language=language
            )
        except Exception as e:
            return GTTSResult(success=False, error=str(e), text=text)
    
    def get_languages(self):
        return self.LANGUAGES
