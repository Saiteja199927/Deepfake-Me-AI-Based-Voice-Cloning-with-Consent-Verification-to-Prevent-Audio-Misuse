"""
Edge TTS Engine
Microsoft Edge Text-to-Speech with multiple voice options
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

# Check availability
EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass


@dataclass
class EdgeTTSResult:
    """Result of Edge TTS synthesis."""
    success: bool
    audio_path: Optional[str] = None
    duration_seconds: float = 0.0
    text: str = ""
    voice: str = ""
    error: Optional[str] = None


class EdgeTTSEngine:
    """
    Microsoft Edge TTS Engine using edge-tts library.
    Free, high-quality voices with no API key required.
    """
    
    # Popular voices
    POPULAR_VOICES = {
        "en-US": [
            ("en-US-JennyNeural", "Jenny", "Female"),
            ("en-US-GuyNeural", "Guy", "Male"),
            ("en-US-AriaNeural", "Aria", "Female"),
            ("en-US-DavisNeural", "Davis", "Male"),
        ],
        "en-GB": [
            ("en-GB-SoniaNeural", "Sonia", "Female"),
            ("en-GB-RyanNeural", "Ryan", "Male"),
        ],
        "es-ES": [
            ("es-ES-ElviraNeural", "Elvira", "Female"),
            ("es-ES-AlvaroNeural", "Alvaro", "Male"),
        ],
        "fr-FR": [
            ("fr-FR-DeniseNeural", "Denise", "Female"),
            ("fr-FR-HenriNeural", "Henri", "Male"),
        ],
        "de-DE": [
            ("de-DE-KatjaNeural", "Katja", "Female"),
            ("de-DE-ConradNeural", "Conrad", "Male"),
        ],
        "hi-IN": [
            ("hi-IN-SwaraNeural", "Swara", "Female"),
            ("hi-IN-MadhurNeural", "Madhur", "Male"),
        ],
    }
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output/tts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.available = EDGE_TTS_AVAILABLE
        self._voices_cache: List[Dict] = []
    
    async def _get_voices(self) -> List[Dict]:
        """Get all available voices."""
        if not self.available:
            return []
        
        if not self._voices_cache:
            voices = await edge_tts.list_voices()
            self._voices_cache = voices
        
        return self._voices_cache
    
    def get_voices_sync(self) -> List[Dict]:
        """Synchronous wrapper to get voices."""
        return asyncio.run(self._get_voices())
    
    async def _synthesize(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        output_path: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> EdgeTTSResult:
        """Async synthesis method."""
        if not self.available:
            return EdgeTTSResult(success=False, error="edge-tts not available")
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"edge_tts_{timestamp}.mp3"
        
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))
            
            return EdgeTTSResult(
                success=True,
                audio_path=str(output_path),
                text=text,
                voice=voice
            )
        except Exception as e:
            return EdgeTTSResult(success=False, error=str(e), text=text)
    
    def synthesize(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        language: str = "en",
        output_path: Optional[str] = None,
        rate: str = "+0%"
    ) -> EdgeTTSResult:
        """Synchronous synthesis method."""
        return asyncio.run(self._synthesize(text, voice, output_path, rate))
    
    def get_popular_voices(self) -> Dict[str, List]:
        """Get popular voices organized by language."""
        return self.POPULAR_VOICES
