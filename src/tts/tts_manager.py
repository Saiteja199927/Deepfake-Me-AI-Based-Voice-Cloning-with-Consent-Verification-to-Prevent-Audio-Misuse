"""
TTS Manager Module
High-level manager for multiple TTS engines
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import engines
from .xtts_engine import XTTSEngine, TTSResult, SpeakerEmbedding


class TTSEngineType(Enum):
    """Available TTS engines."""
    XTTS_V2 = "xtts_v2"
    EDGE_TTS = "edge_tts"
    GTTS = "gtts"
    PYTTSX3 = "pyttsx3"


@dataclass
class VoiceProfile:
    """Profile for a voice configuration."""
    profile_id: str
    name: str
    engine: TTSEngineType
    language: str = "en"
    speaker_audio: Optional[str] = None
    embedding_id: Optional[str] = None
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


class TTSManager:
    """
    High-level TTS manager supporting multiple engines.
    
    Features:
    - Engine selection and fallback
    - Voice profile management
    - Unified synthesis interface
    - Performance monitoring
    """
    
    def __init__(
        self,
        default_engine: TTSEngineType = TTSEngineType.XTTS_V2,
        output_dir: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize TTS Manager.
        
        Args:
            default_engine: Default TTS engine to use
            output_dir: Directory for output audio
            cache_dir: Directory for caching
        """
        self.default_engine = default_engine
        self.output_dir = Path(output_dir) if output_dir else Path("output/tts")
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache/tts")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Engine instances (lazy loaded)
        self._engines: Dict[TTSEngineType, Any] = {}
        
        # Voice profiles
        self._profiles: Dict[str, VoiceProfile] = {}
        
        # Synthesis history
        self._history: List[Dict[str, Any]] = []
    
    def get_engine(self, engine_type: TTSEngineType) -> Any:
        """Get or create an engine instance."""
        if engine_type not in self._engines:
            if engine_type == TTSEngineType.XTTS_V2:
                self._engines[engine_type] = XTTSEngine(
                    output_dir=str(self.output_dir)
                )
            elif engine_type == TTSEngineType.EDGE_TTS:
                from .edge_tts_engine import EdgeTTSEngine
                self._engines[engine_type] = EdgeTTSEngine(
                    output_dir=str(self.output_dir)
                )
            elif engine_type == TTSEngineType.GTTS:
                from .gtts_engine import GTTSEngine
                self._engines[engine_type] = GTTSEngine(
                    output_dir=str(self.output_dir)
                )
            else:
                raise ValueError(f"Unknown engine type: {engine_type}")
        
        return self._engines[engine_type]
    
    def get_xtts_engine(self) -> XTTSEngine:
        """Get the XTTS v2 engine instance."""
        return self.get_engine(TTSEngineType.XTTS_V2)
    
    def synthesize(
        self,
        text: str,
        speaker_audio: Optional[str] = None,
        language: str = "en",
        engine: Optional[TTSEngineType] = None,
        profile_id: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> TTSResult:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            speaker_audio: Reference audio for voice cloning
            language: Language code
            engine: TTS engine to use
            profile_id: Voice profile to use
            output_path: Custom output path
            
        Returns:
            TTSResult with synthesis results
        """
        # Use profile if specified
        if profile_id and profile_id in self._profiles:
            profile = self._profiles[profile_id]
            engine = profile.engine
            language = profile.language
            speaker_audio = profile.speaker_audio
        
        # Default engine
        engine = engine or self.default_engine
        
        # Get engine and synthesize
        tts_engine = self.get_engine(engine)
        
        if engine == TTSEngineType.XTTS_V2:
            if not speaker_audio:
                return TTSResult(
                    success=False,
                    error="XTTS v2 requires a speaker audio reference"
                )
            result = tts_engine.synthesize(
                text=text,
                speaker_audio=speaker_audio,
                language=language,
                output_path=output_path
            )
        else:
            result = tts_engine.synthesize(
                text=text,
                language=language,
                output_path=output_path
            )
        
        # Record history
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "engine": engine.value,
            "text_length": len(text),
            "language": language,
            "success": result.success,
            "duration": result.duration_seconds
        })
        
        return result
    
    def create_profile(
        self,
        profile_id: str,
        name: str,
        engine: TTSEngineType = TTSEngineType.XTTS_V2,
        language: str = "en",
        speaker_audio: Optional[str] = None
    ) -> VoiceProfile:
        """Create a new voice profile."""
        profile = VoiceProfile(
            profile_id=profile_id,
            name=name,
            engine=engine,
            language=language,
            speaker_audio=speaker_audio
        )
        self._profiles[profile_id] = profile
        return profile
    
    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Get a voice profile."""
        return self._profiles.get(profile_id)
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all voice profiles."""
        return [
            {
                "profile_id": p.profile_id,
                "name": p.name,
                "engine": p.engine.value,
                "language": p.language
            }
            for p in self._profiles.values()
        ]
    
    def get_engines_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all available engines."""
        status = {}
        
        # XTTS v2
        try:
            xtts = self.get_engine(TTSEngineType.XTTS_V2)
            status["xtts_v2"] = xtts.get_status()
        except Exception as e:
            status["xtts_v2"] = {"available": False, "error": str(e)}
        
        # Edge TTS
        try:
            import edge_tts
            status["edge_tts"] = {"available": True}
        except:
            status["edge_tts"] = {"available": False}
        
        # gTTS
        try:
            from gtts import gTTS
            status["gtts"] = {"available": True}
        except:
            status["gtts"] = {"available": False}
        
        return status
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent synthesis history."""
        return self._history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get synthesis statistics."""
        total = len(self._history)
        successful = sum(1 for h in self._history if h["success"])
        total_duration = sum(h.get("duration", 0) for h in self._history)
        
        return {
            "total_syntheses": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
            "total_audio_duration": round(total_duration, 2),
            "profiles_count": len(self._profiles),
            "engines_loaded": list(self._engines.keys())
        }
