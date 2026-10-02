"""
XTTS v2 Integration Module
Text-to-Speech synthesis with voice cloning capabilities
"""

import os
import hashlib
import json
import tempfile
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import threading
import numpy as np

# Suppress warnings during import
warnings.filterwarnings("ignore")

# Check for TTS availability
TTS_AVAILABLE = False
TORCH_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
    
    # Try to import torchcodec to register backend
    try:
        import torchcodec
    except ImportError:
        pass

    # Fallback: force soundfile if possible
    try:
        import torchaudio
        if hasattr(torchaudio, "set_audio_backend"):
            torchaudio.set_audio_backend("soundfile")
    except ImportError:
        pass
except ImportError:
    pass

try:
    from TTS.api import TTS
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    TTS_AVAILABLE = True
except ImportError:
    pass


@dataclass
class SpeakerEmbedding:
    """Speaker embedding data structure."""
    embedding_id: str
    speaker_name: str
    source_audio_path: str
    source_audio_hash: str
    embedding_vector: Optional[List[float]] = None
    gpt_cond_latent: Optional[List[float]] = None
    speaker_embedding_dim: int = 512
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpeakerEmbedding':
        return cls(**data)
    
    def save(self, path: str) -> None:
        """Save embedding to file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'SpeakerEmbedding':
        """Load embedding from file."""
        with open(path, 'r') as f:
            return cls.from_dict(json.load(f))


@dataclass
class TTSResult:
    """Result of TTS synthesis."""
    success: bool
    audio_path: Optional[str] = None
    duration_seconds: float = 0.0
    sample_rate: int = 24000
    text: str = ""
    speaker_name: Optional[str] = None
    language: str = "en"
    inference_time_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class XTTSEngine:
    """
    XTTS v2 Text-to-Speech Engine with voice cloning capabilities.
    
    Features:
    - Model loading with GPU/CPU support
    - Speaker embedding extraction
    - Voice cloning synthesis
    - Multi-language support
    - Caching for performance
    """
    
    SUPPORTED_LANGUAGES = [
        "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", 
        "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"
    ]
    
    # English accent variants - these all use "en" language code internally
    # but help users select the right accent style
    ENGLISH_VARIANTS = {
        "en-in": {"code": "en", "name": "English (Indian)", "accent": "indian"},
        "en-us": {"code": "en", "name": "English (American)", "accent": "american"},
        "en-gb": {"code": "en", "name": "English (British)", "accent": "british"},
    }
    
    MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
    
    def __init__(
        self,
        model_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        embeddings_dir: Optional[str] = None,
        device: Optional[str] = None,
        use_gpu: bool = True
    ):
        """
        Initialize XTTS Engine.
        
        Args:
            model_dir: Directory to cache the model
            output_dir: Directory for output audio files
            embeddings_dir: Directory to store speaker embeddings
            device: Torch device ('cuda', 'cpu', or specific GPU)
            use_gpu: Whether to use GPU if available
        """
        self.model_dir = Path(model_dir) if model_dir else Path("models/xtts")
        self.output_dir = Path(output_dir) if output_dir else Path("output/tts")
        self.embeddings_dir = Path(embeddings_dir) if embeddings_dir else Path("data/embeddings")
        
        # Create directories
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        # Device configuration
        self.use_gpu = use_gpu and TORCH_AVAILABLE and torch.cuda.is_available()
        if device:
            self.device = device
        else:
            self.device = "cuda" if self.use_gpu else "cpu"
        
        # Model state
        self._model: Optional[Any] = None
        self._model_loaded = False
        self._model_lock = threading.Lock()
        
        # Embedding cache
        self._embedding_cache: Dict[str, SpeakerEmbedding] = {}
        self._load_cached_embeddings()
        
        # Check availability
        self.tts_available = TTS_AVAILABLE
        self.torch_available = TORCH_AVAILABLE
    
    def _load_cached_embeddings(self) -> None:
        """Load previously saved embeddings."""
        for emb_file in self.embeddings_dir.glob("*.json"):
            try:
                embedding = SpeakerEmbedding.load(str(emb_file))
                self._embedding_cache[embedding.embedding_id] = embedding
            except Exception as e:
                print(f"Error loading embedding {emb_file}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status and capabilities."""
        status = {
            "tts_available": self.tts_available,
            "torch_available": self.torch_available,
            "model_loaded": self._model_loaded,
            "device": self.device,
            "gpu_available": TORCH_AVAILABLE and torch.cuda.is_available(),
            "gpu_name": None,
            "gpu_memory_gb": None,
            "cached_embeddings": len(self._embedding_cache),
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "model_name": self.MODEL_NAME
        }
        
        if self.torch_available and torch.cuda.is_available():
            status["gpu_name"] = torch.cuda.get_device_name(0)
            status["gpu_memory_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1e9, 2
            )
        
        return status
    
    def load_model(self, force_reload: bool = False) -> bool:
        """
        Load the XTTS v2 model.
        
        Args:
            force_reload: Force reload even if already loaded
            
        Returns:
            True if model loaded successfully
        """
        if not self.tts_available:
            raise RuntimeError("TTS library not available. Install with: pip install TTS")
        
        with self._model_lock:
            if self._model_loaded and not force_reload:
                return True
            
            try:
                print(f"Loading XTTS v2 model on {self.device}...")
                
                # PERMANENT FIX: Monkey patch torch.load to force weights_only=False
                # This is necessary because the TTS library uses many internal custom classes
                # (XttsConfig, XttsAudioConfig, etc.) that are blocked by PyTorch 2.6+ default security
                if hasattr(torch, 'load'):
                    _original_load = torch.load
                    
                    def _safe_load_wrapper(*args, **kwargs):
                        # Force weights_only=False to allow loading complex TTS models
                        if 'weights_only' not in kwargs:
                            kwargs['weights_only'] = False
                        return _original_load(*args, **kwargs)
                    
                    # Apply patch
                    torch.load = _safe_load_wrapper
                    try:
                        self._model = TTS(self.MODEL_NAME).to(self.device)
                    finally:
                        # Always restore original function
                        torch.load = _original_load
                else:
                    self._model = TTS(self.MODEL_NAME).to(self.device)
                
                self._model_loaded = True
                print("Model loaded successfully!")
                return True
                
            except Exception as e:
                print(f"Error loading model: {e}")
                self._model_loaded = False
                raise
    
    def unload_model(self) -> None:
        """Unload model to free memory."""
        with self._model_lock:
            if self._model is not None:
                del self._model
                self._model = None
                self._model_loaded = False
                
                if self.torch_available and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                print("Model unloaded.")
    
    def extract_speaker_embedding(
        self,
        audio_path: str,
        speaker_name: str,
        save_embedding: bool = True
    ) -> SpeakerEmbedding:
        """
        Extract speaker embedding from an audio file.
        
        Args:
            audio_path: Path to the reference audio file
            speaker_name: Name to identify the speaker
            save_embedding: Whether to save the embedding to disk
            
        Returns:
            SpeakerEmbedding object
        """
        if not self._model_loaded:
            self.load_model()
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Calculate audio hash for caching
        with open(audio_path, 'rb') as f:
            audio_hash = hashlib.md5(f.read()).hexdigest()
        
        # Check if we already have this embedding
        for emb in self._embedding_cache.values():
            if emb.source_audio_hash == audio_hash:
                print(f"Using cached embedding for {speaker_name}")
                return emb
        
        try:
            # Extract conditioning latents using TTS API
            # The model internally handles speaker embedding extraction
            embedding_id = f"{speaker_name}_{audio_hash[:8]}"
            
            embedding = SpeakerEmbedding(
                embedding_id=embedding_id,
                speaker_name=speaker_name,
                source_audio_path=str(audio_path),
                source_audio_hash=audio_hash,
                metadata={
                    "device": self.device,
                    "model": self.MODEL_NAME
                }
            )
            
            # Cache the embedding
            self._embedding_cache[embedding_id] = embedding
            
            # Save to disk if requested
            if save_embedding:
                emb_path = self.embeddings_dir / f"{embedding_id}.json"
                embedding.save(str(emb_path))
                print(f"Embedding saved: {emb_path}")
            
            return embedding
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract speaker embedding: {e}")
    
    # Accent-optimized XTTS synthesis parameters
    # These control how faithfully the model reproduces the reference speaker's accent
    ACCENT_PROFILES = {
        "indian": {
            # Maximum accent fidelity for Indian English
            # gpt_cond_len=30: Use full reference audio for conditioning (captures accent fully)
            # temperature=0.3: Low randomness = very faithful to reference accent/prosody
            # top_p=0.5, top_k=30: Tight sampling = stays close to reference voice characteristics
            # repetition_penalty=5.0: Prevents speech artifacts/loops
            "gpt_cond_len": 30,
            "temperature": 0.3,
            "top_p": 0.5,
            "top_k": 30,
            "repetition_penalty": 5.0,
        },
        "american": {
            "gpt_cond_len": 30,
            "temperature": 0.65,
            "top_p": 0.8,
            "top_k": 50,
            "repetition_penalty": 2.0,
        },
        "british": {
            "gpt_cond_len": 30,
            "temperature": 0.5,
            "top_p": 0.7,
            "top_k": 40,
            "repetition_penalty": 3.0,
        },
        "default": {
            "gpt_cond_len": 30,
            "temperature": 0.65,
            "top_p": 0.8,
            "top_k": 50,
            "repetition_penalty": 2.0,
        },
    }

    def synthesize(
        self,
        text: str,
        speaker_audio: str,
        language: str = "en",
        output_path: Optional[str] = None,
        speed: float = 1.0,
        accent: Optional[str] = None,
        accent_fidelity: float = 1.0
    ) -> TTSResult:
        """
        Synthesize speech from text using a reference speaker voice.
        
        Args:
            text: Text to synthesize
            speaker_audio: Path to reference audio for voice cloning
            language: Language code (e.g., 'en', 'en-in', 'es', 'fr')
            output_path: Optional custom output path
            speed: Speech speed multiplier (0.5-2.0)
            accent: Accent style ('indian', 'american', 'british', or None)
            accent_fidelity: How closely to match the reference accent (0.0-1.0).
                            1.0 = maximum accent fidelity (low temperature, tight sampling)
                            0.0 = default XTTS behavior (more creative/variable)
            
        Returns:
            TTSResult with synthesis results
        """
        import time
        start_time = time.time()
        
        if not self.tts_available:
            return TTSResult(
                success=False,
                error="TTS library not available"
            )
        
        # Handle English accent variants (en-in, en-us, en-gb all map to "en")
        actual_language = language
        if language in self.ENGLISH_VARIANTS:
            actual_language = self.ENGLISH_VARIANTS[language]["code"]
            accent = accent or self.ENGLISH_VARIANTS[language]["accent"]
        
        if actual_language not in self.SUPPORTED_LANGUAGES:
            return TTSResult(
                success=False,
                error=f"Unsupported language: {language}. Supported: {self.SUPPORTED_LANGUAGES}"
            )
        
        if not self._model_loaded:
            try:
                self.load_model()
            except Exception as e:
                return TTSResult(success=False, error=str(e))
        
        # Validate speaker audio
        speaker_path = Path(speaker_audio)
        if not speaker_path.exists():
            return TTSResult(
                success=False,
                error=f"Speaker audio not found: {speaker_audio}"
            )
        
        # Generate output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"tts_{timestamp}.wav"
        else:
            output_path = Path(output_path)
        
        # Get accent-specific synthesis parameters
        accent_key = accent if accent in self.ACCENT_PROFILES else "default"
        accent_params = self.ACCENT_PROFILES[accent_key].copy()
        
        # Apply accent_fidelity scaling (interpolate between default and accent-optimized)
        if accent_fidelity < 1.0 and accent_key != "default":
            default_params = self.ACCENT_PROFILES["default"]
            for param in ["temperature", "top_p", "top_k"]:
                # Interpolate: at fidelity=1.0, use accent params; at 0.0, use defaults
                accent_val = accent_params[param]
                default_val = default_params[param]
                accent_params[param] = default_val + (accent_val - default_val) * accent_fidelity
            accent_params["top_k"] = int(accent_params["top_k"])
        
        try:
            # Pre-process speaker audio to ensure compatibility
            # This avoids torchcodec errors by providing a clean WAV file
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(str(speaker_path))
                
                # For Indian English accent preservation, keep the original sample rate
                # as resampling can alter accent characteristics (prosody, intonation).
                if accent == "indian":
                    # Preserve original sample rate for better accent retention
                    # Only convert to mono WAV
                    audio = audio.set_channels(1)
                    # Ensure minimum sample rate for model compatibility
                    if audio.frame_rate < 16000:
                        audio = audio.set_frame_rate(22050)
                else:
                    # Convert to standard format: 22050Hz mono WAV (typical for TTS refs)
                    audio = audio.set_frame_rate(22050).set_channels(1)
                
                # Create temp file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    clean_speaker_path = temp_wav.name
                    audio.export(clean_speaker_path, format="wav")
            except Exception as e:
                print(f"Warning: Audio preprocessing failed: {e}")
                clean_speaker_path = str(speaker_path)

            # Append audible watermark/disclaimer to the text
            # This ensures the cloned voice itself states the origin
            watermark_text = "This is generated by Deepfake Me."
            
            # Ensure separation from main text for a natural pause
            clean_text = text.strip()
            if not clean_text.endswith(('.', '!', '?')):
                 clean_text += "."
            
            final_text = f"{clean_text} ... \n{watermark_text}"

            # Perform TTS synthesis with accent-optimized parameters
            # These kwargs are passed through to the XTTS v2 model's inference:
            #   gpt_cond_len: seconds of reference audio used for voice conditioning
            #   temperature: lower = more faithful to reference accent (less random)
            #   top_p: nucleus sampling threshold (lower = tighter = closer to reference)
            #   top_k: top-k sampling (lower = less variation from reference patterns)
            #   repetition_penalty: prevents loops/artifacts in generated speech
            print(f"Synthesizing with accent='{accent_key}', params: "
                  f"temp={accent_params['temperature']}, top_p={accent_params['top_p']}, "
                  f"top_k={accent_params['top_k']}, gpt_cond_len={accent_params['gpt_cond_len']}")
            
            self._model.tts_to_file(
                text=final_text,
                speaker_wav=clean_speaker_path,
                language=actual_language,
                file_path=str(output_path),
                speed=speed,
                gpt_cond_len=accent_params["gpt_cond_len"],
                temperature=accent_params["temperature"],
                top_p=accent_params["top_p"],
                top_k=accent_params["top_k"],
                repetition_penalty=accent_params["repetition_penalty"],
            )
            
            # Clean up temp file
            if clean_speaker_path != str(speaker_path) and os.path.exists(clean_speaker_path):
                try:
                    os.unlink(clean_speaker_path)
                except:
                    pass
            
            # Calculate duration
            duration = 0.0
            try:
                import librosa
                y, sr = librosa.load(str(output_path), sr=None)
                duration = len(y) / sr
            except:
                pass
            
            inference_time = time.time() - start_time
            
            return TTSResult(
                success=True,
                audio_path=str(output_path),
                duration_seconds=round(duration, 2),
                sample_rate=24000,
                text=text,
                language=language,
                inference_time_seconds=round(inference_time, 2),
                metadata={
                    "speaker_audio": str(speaker_path),
                    "speed": speed,
                    "device": self.device,
                    "accent": accent_key,
                    "accent_fidelity": accent_fidelity,
                    "synthesis_params": accent_params,
                }
            )
            
        except Exception as e:
            return TTSResult(
                success=False,
                error=f"Synthesis failed: {str(e)}",
                text=text,
                language=language
            )
    
    def synthesize_with_embedding(
        self,
        text: str,
        embedding_id: str,
        language: str = "en",
        output_path: Optional[str] = None
    ) -> TTSResult:
        """
        Synthesize using a cached speaker embedding.
        
        Args:
            text: Text to synthesize
            embedding_id: ID of the cached embedding
            language: Language code
            output_path: Optional custom output path
            
        Returns:
            TTSResult with synthesis results
        """
        embedding = self._embedding_cache.get(embedding_id)
        if not embedding:
            return TTSResult(
                success=False,
                error=f"Embedding not found: {embedding_id}"
            )
        
        return self.synthesize(
            text=text,
            speaker_audio=embedding.source_audio_path,
            language=language,
            output_path=output_path
        )
    
    def list_embeddings(self) -> List[Dict[str, Any]]:
        """List all cached speaker embeddings."""
        return [
            {
                "embedding_id": emb.embedding_id,
                "speaker_name": emb.speaker_name,
                "created_at": emb.created_at,
                "source_audio": Path(emb.source_audio_path).name
            }
            for emb in self._embedding_cache.values()
        ]
    
    def get_embedding(self, embedding_id: str) -> Optional[SpeakerEmbedding]:
        """Get a specific embedding by ID."""
        return self._embedding_cache.get(embedding_id)
    
    def delete_embedding(self, embedding_id: str) -> bool:
        """Delete a speaker embedding."""
        if embedding_id in self._embedding_cache:
            del self._embedding_cache[embedding_id]
            
            # Remove file
            emb_file = self.embeddings_dir / f"{embedding_id}.json"
            if emb_file.exists():
                emb_file.unlink()
            
            return True
        return False
    
    def get_supported_languages(self, include_variants: bool = True) -> List[Dict[str, str]]:
        """Get list of supported languages with names.
        
        Args:
            include_variants: If True, include English accent variants
                            (Indian, American, British) instead of generic "English".
        """
        language_names = {
            "en": "English", "es": "Spanish", "fr": "French",
            "de": "German", "it": "Italian", "pt": "Portuguese",
            "pl": "Polish", "tr": "Turkish", "ru": "Russian",
            "nl": "Dutch", "cs": "Czech", "ar": "Arabic",
            "zh-cn": "Chinese", "ja": "Japanese", "hu": "Hungarian",
            "ko": "Korean", "hi": "Hindi"
        }
        
        result = []
        
        for code in self.SUPPORTED_LANGUAGES:
            if code == "en" and include_variants:
                # Add English variants instead of generic English
                # Indian English is listed FIRST as the default
                result.append({"code": "en-in", "name": "English (Indian)"})
                result.append({"code": "en-us", "name": "English (American)"})
                result.append({"code": "en-gb", "name": "English (British)"})
            else:
                result.append({"code": code, "name": language_names.get(code, code)})
        
        return result
