"""
Audio Processor Module
Handles audio file processing, conversion, and manipulation
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np

try:
    from pydub import AudioSegment
    from pydub.utils import mediainfo
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from scipy.io import wavfile
from scipy import signal


class AudioProcessor:
    """
    Comprehensive audio processing class for handling various audio operations.
    Supports format conversion, quality analysis, and audio manipulation.
    """
    
    SUPPORTED_FORMATS = ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma']
    SUPPORTED_SAMPLE_RATES = [8000, 16000, 22050, 44100, 48000]
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the AudioProcessor.
        
        Args:
            output_dir: Directory for output files. Uses temp dir if not specified.
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check available backends
        self.pydub_available = PYDUB_AVAILABLE
        self.librosa_available = LIBROSA_AVAILABLE
    
    # ==================== FILE VALIDATION ====================
    
    def validate_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate an audio file and return detailed information.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing validation results and file info
        """
        result = {
            "valid": False,
            "error": None,
            "file_info": {},
            "warnings": []
        }
        
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            result["error"] = "File does not exist"
            return result
        
        # Check file extension
        extension = path.suffix.lower().lstrip('.')
        if extension not in self.SUPPORTED_FORMATS:
            result["error"] = f"Unsupported format: {extension}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            return result
        
        # Check file size
        file_size = path.stat().st_size
        if file_size == 0:
            result["error"] = "File is empty"
            return result
        
        if file_size > 100 * 1024 * 1024:  # 100 MB limit
            result["warnings"].append("File is larger than 100MB, processing may be slow")
        
        # Try to load and get audio info
        try:
            audio_info = self.get_audio_info(file_path)
            result["file_info"] = audio_info
            result["valid"] = True
            
            # Add warnings for potential issues
            if audio_info.get("sample_rate", 0) < 16000:
                result["warnings"].append("Low sample rate may affect audio quality")
            
            if audio_info.get("duration", 0) > 3600:
                result["warnings"].append("Audio longer than 1 hour, processing may be slow")
                
        except Exception as e:
            result["error"] = f"Failed to read audio file: {str(e)}"
        
        return result
    
    def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed information about an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing audio metadata
        """
        info = {
            "file_path": str(file_path),
            "file_name": Path(file_path).name,
            "format": Path(file_path).suffix.lower().lstrip('.'),
            "file_size_bytes": Path(file_path).stat().st_size,
            "file_size_mb": round(Path(file_path).stat().st_size / (1024 * 1024), 2)
        }
        
        if self.pydub_available:
            try:
                audio = AudioSegment.from_file(file_path)
                info.update({
                    "duration": round(len(audio) / 1000, 2),  # seconds
                    "duration_formatted": self._format_duration(len(audio) / 1000),
                    "sample_rate": audio.frame_rate,
                    "channels": audio.channels,
                    "sample_width": audio.sample_width,
                    "bit_depth": audio.sample_width * 8,
                    "frame_count": audio.frame_count(),
                    "bitrate_kbps": self._calculate_bitrate(file_path, len(audio) / 1000)
                })
            except Exception as e:
                info["error"] = str(e)
        
        elif self.librosa_available:
            try:
                y, sr = librosa.load(file_path, sr=None)
                duration = librosa.get_duration(y=y, sr=sr)
                info.update({
                    "duration": round(duration, 2),
                    "duration_formatted": self._format_duration(duration),
                    "sample_rate": sr,
                    "channels": 1 if y.ndim == 1 else y.shape[0],
                    "frame_count": len(y)
                })
            except Exception as e:
                info["error"] = str(e)
        
        return info
    
    # ==================== FORMAT CONVERSION ====================
    
    def convert_format(
        self, 
        input_path: str, 
        output_format: str,
        output_path: Optional[str] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        bitrate: Optional[str] = None
    ) -> str:
        """
        Convert audio file to a different format.
        
        Args:
            input_path: Path to input audio file
            output_format: Target format (mp3, wav, ogg, flac, etc.)
            output_path: Optional custom output path
            sample_rate: Optional target sample rate
            channels: Optional target number of channels (1 for mono, 2 for stereo)
            bitrate: Optional bitrate for lossy formats (e.g., "192k")
            
        Returns:
            Path to the converted audio file
        """
        if not self.pydub_available:
            raise RuntimeError("pydub is required for format conversion")
        
        output_format = output_format.lower().lstrip('.')
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Load audio
        audio = AudioSegment.from_file(input_path)
        
        # Apply transformations
        if sample_rate:
            audio = audio.set_frame_rate(sample_rate)
        
        if channels:
            if channels == 1:
                audio = audio.set_channels(1)
            elif channels == 2:
                audio = audio.set_channels(2)
        
        # Determine output path
        if not output_path:
            input_name = Path(input_path).stem
            output_path = self.output_dir / f"{input_name}.{output_format}"
        
        # Export with appropriate settings
        export_params = {}
        if bitrate and output_format in ['mp3', 'ogg', 'aac']:
            export_params['bitrate'] = bitrate
        
        audio.export(str(output_path), format=output_format, **export_params)
        
        return str(output_path)
    
    def batch_convert(
        self,
        input_files: list,
        output_format: str,
        output_dir: Optional[str] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Convert multiple audio files to a target format.
        
        Args:
            input_files: List of input file paths
            output_format: Target format
            output_dir: Optional output directory
            **kwargs: Additional arguments passed to convert_format
            
        Returns:
            Dictionary mapping input paths to output paths
        """
        results = {}
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        
        for input_file in input_files:
            try:
                output_path = out_dir / f"{Path(input_file).stem}.{output_format}"
                converted = self.convert_format(
                    input_file, 
                    output_format, 
                    str(output_path),
                    **kwargs
                )
                results[input_file] = {"success": True, "output": converted}
            except Exception as e:
                results[input_file] = {"success": False, "error": str(e)}
        
        return results
    
    # ==================== QUALITY CHECKS ====================
    
    def analyze_quality(self, file_path: str) -> Dict[str, Any]:
        """
        Perform comprehensive quality analysis on an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing quality metrics and recommendations
        """
        quality_report = {
            "file_path": file_path,
            "metrics": {},
            "issues": [],
            "recommendations": [],
            "quality_score": 0
        }
        
        try:
            # Load audio for analysis
            if self.librosa_available:
                y, sr = librosa.load(file_path, sr=None)
            elif self.pydub_available:
                audio = AudioSegment.from_file(file_path)
                y = np.array(audio.get_array_of_samples()).astype(np.float32)
                y = y / np.max(np.abs(y)) if np.max(np.abs(y)) > 0 else y
                sr = audio.frame_rate
            else:
                raise RuntimeError("Neither librosa nor pydub is available")
            
            # Calculate metrics
            metrics = {}
            
            # Duration check
            duration = len(y) / sr
            metrics["duration_seconds"] = round(duration, 2)
            
            # Sample rate check
            metrics["sample_rate"] = sr
            if sr < 16000:
                quality_report["issues"].append("Low sample rate (< 16kHz)")
                quality_report["recommendations"].append("Consider using audio with at least 16kHz sample rate")
            elif sr < 22050:
                quality_report["issues"].append("Sample rate below standard (< 22.05kHz)")
            
            # RMS Energy (Volume) analysis
            rms = np.sqrt(np.mean(y**2))
            metrics["rms_energy"] = round(float(rms), 4)
            metrics["rms_db"] = round(20 * np.log10(rms + 1e-10), 2)
            
            if rms < 0.01:
                quality_report["issues"].append("Very low audio volume")
                quality_report["recommendations"].append("Consider normalizing or re-recording with higher volume")
            
            # Peak amplitude
            peak = np.max(np.abs(y))
            metrics["peak_amplitude"] = round(float(peak), 4)
            
            if peak > 0.99:
                quality_report["issues"].append("Audio may be clipping (peak near 1.0)")
                quality_report["recommendations"].append("Reduce volume to prevent distortion")
            
            # Dynamic range
            if peak > 0:
                dynamic_range_db = 20 * np.log10(peak / (rms + 1e-10))
                metrics["dynamic_range_db"] = round(dynamic_range_db, 2)
            
            # Silence detection
            silence_threshold = 0.01
            silence_ratio = np.sum(np.abs(y) < silence_threshold) / len(y)
            metrics["silence_ratio"] = round(silence_ratio, 4)
            
            if silence_ratio > 0.5:
                quality_report["issues"].append("More than 50% silence in audio")
                quality_report["recommendations"].append("Trim silence or check recording")
            
            # Noise estimation (simple approach using lowest energy frames)
            if self.librosa_available:
                noise_metrics = self._estimate_noise(y, sr)
                metrics.update(noise_metrics)
                
                if noise_metrics.get("estimated_snr_db", 100) < 20:
                    quality_report["issues"].append("High noise level detected")
                    quality_report["recommendations"].append("Consider noise reduction processing")
            
            # Zero crossing rate (can indicate noise or speech)
            zcr = np.mean(np.abs(np.diff(np.signbit(y))))
            metrics["zero_crossing_rate"] = round(float(zcr), 4)
            
            quality_report["metrics"] = metrics
            
            # Calculate overall quality score (0-100)
            quality_report["quality_score"] = self._calculate_quality_score(metrics, quality_report["issues"])
            
        except Exception as e:
            quality_report["error"] = str(e)
        
        return quality_report
    
    def check_sample_rate(self, file_path: str, target_rate: int = 22050) -> Dict[str, Any]:
        """
        Check if audio meets sample rate requirements.
        
        Args:
            file_path: Path to audio file
            target_rate: Target sample rate to check against
            
        Returns:
            Dictionary with sample rate info and compliance status
        """
        info = self.get_audio_info(file_path)
        current_rate = info.get("sample_rate", 0)
        
        return {
            "current_sample_rate": current_rate,
            "target_sample_rate": target_rate,
            "meets_requirement": current_rate >= target_rate,
            "needs_upsampling": current_rate < target_rate,
            "needs_downsampling": current_rate > target_rate,
            "recommendation": self._get_sample_rate_recommendation(current_rate, target_rate)
        }
    
    def check_duration(
        self, 
        file_path: str, 
        min_duration: float = 0.5, 
        max_duration: float = 3600
    ) -> Dict[str, Any]:
        """
        Check if audio duration is within acceptable range.
        
        Args:
            file_path: Path to audio file
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            
        Returns:
            Dictionary with duration info and compliance status
        """
        info = self.get_audio_info(file_path)
        duration = info.get("duration", 0)
        
        return {
            "duration_seconds": duration,
            "duration_formatted": self._format_duration(duration),
            "min_duration": min_duration,
            "max_duration": max_duration,
            "is_valid": min_duration <= duration <= max_duration,
            "too_short": duration < min_duration,
            "too_long": duration > max_duration
        }
    
    def detect_noise_level(self, file_path: str) -> Dict[str, Any]:
        """
        Detect and analyze noise levels in audio.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with noise analysis results
        """
        if not self.librosa_available:
            return {"error": "librosa is required for noise detection"}
        
        try:
            y, sr = librosa.load(file_path, sr=None)
            noise_metrics = self._estimate_noise(y, sr)
            
            # Classify noise level
            snr = noise_metrics.get("estimated_snr_db", 0)
            if snr >= 40:
                noise_level = "Excellent"
                description = "Very clean audio with minimal noise"
            elif snr >= 30:
                noise_level = "Good"
                description = "Clean audio suitable for most applications"
            elif snr >= 20:
                noise_level = "Acceptable"
                description = "Some noise present but still usable"
            elif snr >= 10:
                noise_level = "Poor"
                description = "Noticeable noise that may affect quality"
            else:
                noise_level = "Very Poor"
                description = "High noise level, consider re-recording"
            
            return {
                **noise_metrics,
                "noise_level": noise_level,
                "description": description,
                "requires_denoising": snr < 25
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== AUDIO MANIPULATION ====================
    
    def normalize_audio(
        self, 
        file_path: str, 
        target_db: float = -3.0,
        output_path: Optional[str] = None
    ) -> str:
        """
        Normalize audio to a target dB level.
        
        Args:
            file_path: Path to input audio
            target_db: Target dB level (default -3.0 dB)
            output_path: Optional output path
            
        Returns:
            Path to normalized audio file
        """
        if not self.pydub_available:
            raise RuntimeError("pydub is required for audio normalization")
        
        audio = AudioSegment.from_file(file_path)
        
        # Calculate change needed
        change_db = target_db - audio.dBFS
        normalized = audio.apply_gain(change_db)
        
        # Determine output path
        if not output_path:
            stem = Path(file_path).stem
            ext = Path(file_path).suffix
            output_path = self.output_dir / f"{stem}_normalized{ext}"
        
        normalized.export(str(output_path), format=Path(output_path).suffix.lstrip('.'))
        
        return str(output_path)
    
    def trim_silence(
        self,
        file_path: str,
        silence_threshold: int = -40,
        min_silence_len: int = 500,
        output_path: Optional[str] = None
    ) -> str:
        """
        Remove silence from the beginning and end of audio.
        
        Args:
            file_path: Path to input audio
            silence_threshold: Silence threshold in dB
            min_silence_len: Minimum silence length in ms
            output_path: Optional output path
            
        Returns:
            Path to trimmed audio file
        """
        if not self.pydub_available:
            raise RuntimeError("pydub is required for silence trimming")
        
        from pydub.silence import detect_leading_silence
        
        audio = AudioSegment.from_file(file_path)
        
        # Detect and trim leading silence
        start_trim = detect_leading_silence(audio, silence_threshold=silence_threshold)
        
        # Detect and trim trailing silence (reverse, detect, reverse back)
        end_trim = detect_leading_silence(audio.reverse(), silence_threshold=silence_threshold)
        
        # Apply trim
        duration = len(audio)
        trimmed = audio[start_trim:duration - end_trim]
        
        # Determine output path
        if not output_path:
            stem = Path(file_path).stem
            ext = Path(file_path).suffix
            output_path = self.output_dir / f"{stem}_trimmed{ext}"
        
        trimmed.export(str(output_path), format=Path(output_path).suffix.lstrip('.'))
        
        return str(output_path)
    
    def resample(
        self,
        file_path: str,
        target_sample_rate: int,
        output_path: Optional[str] = None
    ) -> str:
        """
        Resample audio to a target sample rate.
        
        Args:
            file_path: Path to input audio
            target_sample_rate: Target sample rate in Hz
            output_path: Optional output path
            
        Returns:
            Path to resampled audio file
        """
        if not self.pydub_available:
            raise RuntimeError("pydub is required for resampling")
        
        audio = AudioSegment.from_file(file_path)
        resampled = audio.set_frame_rate(target_sample_rate)
        
        # Determine output path
        if not output_path:
            stem = Path(file_path).stem
            ext = Path(file_path).suffix
            output_path = self.output_dir / f"{stem}_{target_sample_rate}hz{ext}"
        
        resampled.export(str(output_path), format=Path(output_path).suffix.lstrip('.'))
        
        return str(output_path)
    
    # ==================== HELPER METHODS ====================
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    def _calculate_bitrate(self, file_path: str, duration: float) -> int:
        """Calculate approximate bitrate in kbps."""
        if duration <= 0:
            return 0
        file_size_bits = Path(file_path).stat().st_size * 8
        return int(file_size_bits / duration / 1000)
    
    def _estimate_noise(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """Estimate noise level using frame-based analysis."""
        # Split into frames
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop
        
        # Calculate energy for each frame
        frames = librosa.util.frame(y, frame_length=frame_length, hop_length=hop_length)
        frame_energy = np.sum(frames**2, axis=0)
        
        # Estimate noise from lowest energy frames (bottom 10%)
        sorted_energy = np.sort(frame_energy)
        noise_percentile = 10
        noise_threshold_idx = int(len(sorted_energy) * noise_percentile / 100)
        noise_floor = np.mean(sorted_energy[:max(1, noise_threshold_idx)])
        
        # Estimate signal from highest energy frames (top 10%)
        signal_threshold_idx = int(len(sorted_energy) * (100 - noise_percentile) / 100)
        signal_level = np.mean(sorted_energy[signal_threshold_idx:])
        
        # Calculate SNR
        if noise_floor > 0:
            snr_db = 10 * np.log10(signal_level / noise_floor)
        else:
            snr_db = 60  # Assume excellent SNR if no detectable noise
        
        return {
            "noise_floor_energy": round(float(noise_floor), 6),
            "signal_energy": round(float(signal_level), 6),
            "estimated_snr_db": round(float(snr_db), 2)
        }
    
    def _calculate_quality_score(self, metrics: Dict, issues: list) -> int:
        """Calculate overall quality score from 0-100."""
        score = 100
        
        # Deduct for issues
        score -= len(issues) * 10
        
        # Deduct for low sample rate
        sr = metrics.get("sample_rate", 44100)
        if sr < 16000:
            score -= 20
        elif sr < 22050:
            score -= 10
        
        # Deduct for silence
        silence_ratio = metrics.get("silence_ratio", 0)
        if silence_ratio > 0.7:
            score -= 30
        elif silence_ratio > 0.5:
            score -= 15
        
        # Deduct for noise
        snr = metrics.get("estimated_snr_db", 40)
        if snr < 10:
            score -= 30
        elif snr < 20:
            score -= 15
        elif snr < 30:
            score -= 5
        
        return max(0, min(100, score))
    
    def _get_sample_rate_recommendation(self, current: int, target: int) -> str:
        """Get recommendation for sample rate adjustment."""
        if current >= target:
            return "Sample rate is sufficient"
        elif current >= 16000:
            return "Consider upsampling for better quality"
        else:
            return "Sample rate is too low, re-recording recommended"
