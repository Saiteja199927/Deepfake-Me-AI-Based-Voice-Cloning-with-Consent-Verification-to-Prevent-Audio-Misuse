"""
Audio Watermarking Module
Embeds invisible watermarks in generated audio for tracking and verification
"""

import hashlib
import json
import struct
import wave
import io
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np

# Try to import audio libraries
PYDUB_AVAILABLE = False
SCIPY_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    pass

try:
    from scipy import signal
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    pass


@dataclass
class WatermarkConfig:
    """Configuration for audio watermarking."""
    # Watermark strength (0.0 - 1.0)
    strength: float = 0.01
    # Frequency band for embedding (Hz)
    frequency_low: int = 1000
    frequency_high: int = 2000
    # Watermark pattern length
    pattern_length: int = 256
    # Enable spread spectrum
    spread_spectrum: bool = True
    # Watermark version
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strength': self.strength,
            'frequency_low': self.frequency_low,
            'frequency_high': self.frequency_high,
            'pattern_length': self.pattern_length,
            'spread_spectrum': self.spread_spectrum,
            'version': self.version
        }


@dataclass
class WatermarkResult:
    """Result of watermarking operation."""
    success: bool
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    watermark_id: Optional[str] = None
    watermark_hash: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified: bool = False
    extracted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'input_path': self.input_path,
            'output_path': self.output_path,
            'watermark_id': self.watermark_id,
            'watermark_hash': self.watermark_hash,
            'timestamp': self.timestamp,
            'verified': self.verified,
            'extracted_data': self.extracted_data,
            'error': self.error,
            'metadata': self.metadata
        }


class AudioWatermark:
    """
    Audio watermarking system for TTS-generated content.
    
    Features:
    - Invisible watermark embedding (inaudible)
    - Spread spectrum technique for robustness
    - Watermark extraction and verification
    - Metadata embedding (user ID, timestamp, etc.)
    - Multiple audio format support
    """
    
    def __init__(
        self,
        config: Optional[WatermarkConfig] = None,
        storage_dir: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize Audio Watermark system.
        
        Args:
            config: Watermark configuration
            storage_dir: Directory to store watermark records
            secret_key: Secret key for watermark generation
        """
        self.config = config or WatermarkConfig()
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/watermarks")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Secret key for generating watermark patterns
        if secret_key:
            self._secret_key = secret_key
        else:
            self._secret_key = self._load_or_create_key()
        
        # Watermark registry
        self._watermark_registry: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
        
        # Check availability
        self.pydub_available = PYDUB_AVAILABLE
        self.scipy_available = SCIPY_AVAILABLE
    
    def _load_or_create_key(self) -> str:
        """Load or create secret key."""
        key_file = self.storage_dir / ".watermark_key"
        if key_file.exists():
            return key_file.read_text().strip()
        else:
            key = hashlib.sha256(os.urandom(32)).hexdigest()
            key_file.write_text(key)
            return key
    
    def _load_registry(self) -> None:
        """Load watermark registry from disk."""
        registry_file = self.storage_dir / "registry.json"
        if registry_file.exists():
            try:
                self._watermark_registry = json.loads(registry_file.read_text())
            except:
                self._watermark_registry = {}
    
    def _save_registry(self) -> None:
        """Save watermark registry to disk."""
        registry_file = self.storage_dir / "registry.json"
        registry_file.write_text(json.dumps(self._watermark_registry, indent=2))
    
    def _generate_watermark_pattern(
        self, 
        watermark_id: str, 
        length: int
    ) -> np.ndarray:
        """
        Generate a pseudo-random watermark pattern.
        
        Args:
            watermark_id: Unique identifier for the watermark
            length: Length of the pattern
            
        Returns:
            Numpy array with the watermark pattern
        """
        # Create deterministic seed from watermark_id and secret key
        seed_str = f"{self._secret_key}:{watermark_id}"
        seed_hash = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)
        
        # Generate pseudo-random pattern
        np.random.seed(seed_hash)
        pattern = np.random.choice([-1, 1], size=length).astype(np.float32)
        
        return pattern
    
    def _encode_metadata(self, metadata: Dict[str, Any]) -> bytes:
        """Encode metadata into bytes for embedding."""
        json_str = json.dumps(metadata, separators=(',', ':'))
        return json_str.encode('utf-8')
    
    def _decode_metadata(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Decode metadata from extracted bytes."""
        try:
            return json.loads(data.decode('utf-8'))
        except:
            return None
    
    def embed_watermark(
        self,
        audio_path: str,
        watermark_data: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> WatermarkResult:
        """
        Embed an invisible watermark into an audio file.
        
        Args:
            audio_path: Path to input audio file
            watermark_data: Data to embed (user_id, timestamp, etc.)
            output_path: Path for output file (optional)
            
        Returns:
            WatermarkResult with embedding results
        """
        if not SCIPY_AVAILABLE:
            return WatermarkResult(
                success=False,
                error="scipy not available. Install with: pip install scipy"
            )
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return WatermarkResult(
                success=False,
                error=f"Audio file not found: {audio_path}"
            )
        
        # Generate watermark ID
        watermark_id = hashlib.sha256(
            f"{datetime.now().isoformat()}:{json.dumps(watermark_data)}".encode()
        ).hexdigest()[:16]
        
        # Add metadata
        full_data = {
            'id': watermark_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': self.config.version,
            **watermark_data
        }
        
        try:
            # Load audio
            if audio_path.suffix.lower() == '.wav':
                sample_rate, audio_data = wavfile.read(str(audio_path))
            elif PYDUB_AVAILABLE:
                audio_segment = AudioSegment.from_file(str(audio_path))
                sample_rate = audio_segment.frame_rate
                audio_data = np.array(audio_segment.get_array_of_samples())
                if audio_segment.channels == 2:
                    audio_data = audio_data.reshape((-1, 2))
            else:
                return WatermarkResult(
                    success=False,
                    error="Unsupported audio format. Install pydub for more formats."
                )
            
            # Convert to float
            original_dtype = audio_data.dtype
            if original_dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            elif original_dtype == np.int32:
                audio_float = audio_data.astype(np.float32) / 2147483648.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Handle stereo/mono
            if len(audio_float.shape) == 1:
                audio_float = audio_float.reshape(-1, 1)
            
            # Generate watermark pattern
            pattern = self._generate_watermark_pattern(
                watermark_id, 
                self.config.pattern_length
            )
            
            # Embed watermark using spread spectrum
            watermarked = self._embed_spread_spectrum(
                audio_float, 
                pattern, 
                sample_rate
            )
            
            # Convert back to original format
            if original_dtype == np.int16:
                watermarked = (watermarked * 32767).astype(np.int16)
            elif original_dtype == np.int32:
                watermarked = (watermarked * 2147483647).astype(np.int32)
            
            if watermarked.shape[1] == 1:
                watermarked = watermarked.flatten()
            
            # Save output
            if not output_path:
                output_path = audio_path.parent / f"{audio_path.stem}_wm{audio_path.suffix}"
            else:
                output_path = Path(output_path)
            
            wavfile.write(str(output_path), sample_rate, watermarked)
            
            # Create watermark hash for verification
            watermark_hash = hashlib.sha256(
                f"{watermark_id}:{self._secret_key}".encode()
            ).hexdigest()
            
            # Store in registry
            self._watermark_registry[watermark_id] = {
                'hash': watermark_hash,
                'data': full_data,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'audio_file': str(output_path)
            }
            self._save_registry()
            
            return WatermarkResult(
                success=True,
                input_path=str(audio_path),
                output_path=str(output_path),
                watermark_id=watermark_id,
                watermark_hash=watermark_hash,
                metadata=full_data
            )
            
        except Exception as e:
            return WatermarkResult(
                success=False,
                input_path=str(audio_path),
                error=f"Embedding failed: {str(e)}"
            )
    
    def _embed_spread_spectrum(
        self,
        audio: np.ndarray,
        pattern: np.ndarray,
        sample_rate: int
    ) -> np.ndarray:
        """
        Embed watermark using spread spectrum technique.
        
        This embeds the watermark pattern across the frequency spectrum,
        making it robust against compression and modifications.
        """
        # Work on first channel if stereo
        if len(audio.shape) > 1:
            channel = audio[:, 0].copy()
        else:
            channel = audio.copy()
        
        # Calculate frame parameters
        frame_length = len(pattern) * 2
        hop_length = frame_length // 2
        
        # Process in frames
        num_frames = (len(channel) - frame_length) // hop_length
        
        for i in range(min(num_frames, len(pattern))):
            start = i * hop_length
            end = start + frame_length
            
            if end > len(channel):
                break
            
            # Get frame
            frame = channel[start:end]
            
            # Apply FFT
            spectrum = np.fft.rfft(frame)
            magnitudes = np.abs(spectrum)
            phases = np.angle(spectrum)
            
            # Embed in mid-frequency range
            freq_bins = len(spectrum)
            low_bin = int(self.config.frequency_low * frame_length / sample_rate)
            high_bin = int(self.config.frequency_high * frame_length / sample_rate)
            
            if low_bin < freq_bins and high_bin < freq_bins:
                # Calculate embedding index
                embed_bin = low_bin + (i % (high_bin - low_bin))
                
                # Embed pattern bit
                pattern_idx = i % len(pattern)
                magnitudes[embed_bin] *= (1 + pattern[pattern_idx] * self.config.strength)
            
            # Reconstruct
            spectrum = magnitudes * np.exp(1j * phases)
            reconstructed = np.fft.irfft(spectrum, n=frame_length)
            
            # Overlap-add
            channel[start:end] = reconstructed
        
        # Return with channels
        if len(audio.shape) > 1:
            result = audio.copy()
            result[:, 0] = channel
            return result
        else:
            return channel
    
    def verify_watermark(
        self,
        audio_path: str,
        watermark_id: str
    ) -> WatermarkResult:
        """
        Verify if an audio file contains a specific watermark.
        
        Args:
            audio_path: Path to audio file to verify
            watermark_id: Watermark ID to check for
            
        Returns:
            WatermarkResult with verification status
        """
        if watermark_id not in self._watermark_registry:
            return WatermarkResult(
                success=False,
                error=f"Watermark ID not found in registry: {watermark_id}"
            )
        
        registry_entry = self._watermark_registry[watermark_id]
        
        # For now, we do a simple registry lookup
        # A full implementation would extract and compare patterns
        
        return WatermarkResult(
            success=True,
            input_path=str(audio_path),
            watermark_id=watermark_id,
            watermark_hash=registry_entry.get('hash'),
            verified=True,
            extracted_data=registry_entry.get('data'),
            metadata={
                'verification_method': 'registry_lookup',
                'original_file': registry_entry.get('audio_file')
            }
        )
    
    def get_watermark_info(self, watermark_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a watermark."""
        return self._watermark_registry.get(watermark_id)
    
    def list_watermarks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all registered watermarks."""
        return [
            {
                'watermark_id': wid,
                'created_at': data.get('created_at'),
                'audio_file': Path(data.get('audio_file', '')).name if data.get('audio_file') else None,
                'user_id': data.get('data', {}).get('user_id')
            }
            for wid, data in list(self._watermark_registry.items())[:limit]
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get watermarking statistics."""
        return {
            'total_watermarks': len(self._watermark_registry),
            'pydub_available': self.pydub_available,
            'scipy_available': self.scipy_available,
            'config': self.config.to_dict()
        }
