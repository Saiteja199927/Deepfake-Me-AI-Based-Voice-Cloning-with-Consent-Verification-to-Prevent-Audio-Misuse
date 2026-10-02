"""
Audio Validator Module
Handles audio file validation and format checking
"""

import os
import struct
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class AudioFormat(Enum):
    """Supported audio formats with their properties."""
    MP3 = ("mp3", ["audio/mpeg", "audio/mp3"], b"\xff\xfb", b"\xff\xfa", b"\xff\xf3", b"\xff\xf2", b"ID3")
    WAV = ("wav", ["audio/wav", "audio/x-wav"], b"RIFF")
    OGG = ("ogg", ["audio/ogg", "application/ogg"], b"OggS")
    FLAC = ("flac", ["audio/flac", "audio/x-flac"], b"fLaC")
    M4A = ("m4a", ["audio/mp4", "audio/x-m4a"], b"ftyp")
    AAC = ("aac", ["audio/aac"], b"\xff\xf1", b"\xff\xf9")
    WMA = ("wma", ["audio/x-ms-wma"], b"\x30\x26\xb2\x75")


@dataclass
class ValidationResult:
    """Result of audio file validation."""
    is_valid: bool
    file_path: str
    file_name: str
    file_size_bytes: int
    detected_format: Optional[str]
    extension: str
    errors: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "file_size_mb": round(self.file_size_bytes / (1024 * 1024), 2),
            "detected_format": self.detected_format,
            "extension": self.extension,
            "errors": self.errors,
            "warnings": self.warnings
        }


class AudioValidator:
    """
    Validates audio files for format, integrity, and quality requirements.
    """
    
    # File size limits
    MIN_FILE_SIZE = 1024  # 1 KB
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
    WARN_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    
    # Duration limits (in seconds)
    MIN_DURATION = 0.1
    MAX_DURATION = 7200  # 2 hours
    WARN_DURATION = 3600  # 1 hour
    
    # Quality thresholds
    MIN_SAMPLE_RATE = 8000
    RECOMMENDED_SAMPLE_RATE = 22050
    MIN_BIT_DEPTH = 8
    
    def __init__(self):
        """Initialize the AudioValidator."""
        self.supported_extensions = [fmt.value[0] for fmt in AudioFormat]
    
    def validate(
        self,
        file_path: str,
        check_content: bool = True,
        max_size_mb: Optional[float] = None,
        allowed_formats: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate an audio file.
        
        Args:
            file_path: Path to the audio file
            check_content: Whether to check file content/magic bytes
            max_size_mb: Optional maximum file size in MB
            allowed_formats: Optional list of allowed formats
            
        Returns:
            ValidationResult with detailed validation info
        """
        errors = []
        warnings = []
        detected_format = None
        
        path = Path(file_path)
        file_size = 0
        extension = ""
        
        # Check if file exists
        if not path.exists():
            errors.append("File does not exist")
            return ValidationResult(
                is_valid=False,
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=0,
                detected_format=None,
                extension="",
                errors=errors,
                warnings=warnings
            )
        
        # Check if it's a file (not directory)
        if not path.is_file():
            errors.append("Path is not a file")
            return ValidationResult(
                is_valid=False,
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=0,
                detected_format=None,
                extension="",
                errors=errors,
                warnings=warnings
            )
        
        # Get file info
        file_size = path.stat().st_size
        extension = path.suffix.lower().lstrip('.')
        
        # Check file size
        if file_size < self.MIN_FILE_SIZE:
            errors.append(f"File too small ({file_size} bytes). Minimum: {self.MIN_FILE_SIZE} bytes")
        
        max_size = (max_size_mb * 1024 * 1024) if max_size_mb else self.MAX_FILE_SIZE
        if file_size > max_size:
            errors.append(f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum: {max_size / 1024 / 1024:.1f} MB")
        elif file_size > self.WARN_FILE_SIZE:
            warnings.append(f"Large file ({file_size / 1024 / 1024:.1f} MB). Processing may be slow.")
        
        # Check extension
        formats_to_check = allowed_formats if allowed_formats else self.supported_extensions
        if extension not in formats_to_check:
            errors.append(f"Unsupported format: .{extension}. Allowed: {', '.join(formats_to_check)}")
        
        # Check file content (magic bytes)
        if check_content and file_size > 0:
            detected_format = self._detect_format(path)
            if detected_format:
                if extension and detected_format != extension:
                    warnings.append(
                        f"File extension (.{extension}) doesn't match detected format ({detected_format})"
                    )
            else:
                warnings.append("Could not detect audio format from file content")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            file_path=str(path),
            file_name=path.name,
            file_size_bytes=file_size,
            detected_format=detected_format,
            extension=extension,
            errors=errors,
            warnings=warnings
        )
    
    def validate_upload(
        self,
        file_content: bytes,
        file_name: str,
        max_size_mb: float = 100
    ) -> ValidationResult:
        """
        Validate uploaded file content (for Streamlit uploads).
        
        Args:
            file_content: Raw file bytes
            file_name: Original filename
            max_size_mb: Maximum allowed size in MB
            
        Returns:
            ValidationResult with validation info
        """
        errors = []
        warnings = []
        
        file_size = len(file_content)
        extension = Path(file_name).suffix.lower().lstrip('.')
        
        # Check size
        if file_size < self.MIN_FILE_SIZE:
            errors.append(f"File too small ({file_size} bytes)")
        
        max_size = max_size_mb * 1024 * 1024
        if file_size > max_size:
            errors.append(f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum: {max_size_mb} MB")
        
        # Check extension
        if extension not in self.supported_extensions:
            errors.append(f"Unsupported format: .{extension}")
        
        # Detect format from content
        detected_format = self._detect_format_from_bytes(file_content[:32])
        
        if detected_format:
            if extension and detected_format != extension:
                warnings.append(f"Extension (.{extension}) doesn't match content ({detected_format})")
        else:
            warnings.append("Could not verify audio format from content")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            file_path="<uploaded>",
            file_name=file_name,
            file_size_bytes=file_size,
            detected_format=detected_format,
            extension=extension,
            errors=errors,
            warnings=warnings
        )
    
    def _detect_format(self, file_path: Path) -> Optional[str]:
        """Detect audio format from file magic bytes."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)
            return self._detect_format_from_bytes(header)
        except Exception:
            return None
    
    def _detect_format_from_bytes(self, header: bytes) -> Optional[str]:
        """Detect audio format from header bytes."""
        if len(header) < 4:
            return None
        
        # Check each format
        for fmt in AudioFormat:
            format_name, mime_types, *signatures = fmt.value
            for sig in signatures:
                if isinstance(sig, bytes):
                    if header.startswith(sig):
                        return format_name
                    # Special handling for M4A (ftyp appears at offset 4)
                    if format_name == "m4a" and sig in header[:12]:
                        return format_name
        
        return None
    
    def get_supported_formats(self) -> List[Dict[str, Any]]:
        """Get list of supported formats with details."""
        return [
            {
                "extension": fmt.value[0],
                "mime_types": fmt.value[1],
                "name": fmt.name
            }
            for fmt in AudioFormat
        ]
    
    def is_valid_extension(self, extension: str) -> bool:
        """Check if file extension is supported."""
        return extension.lower().lstrip('.') in self.supported_extensions


class UploadHandler:
    """
    Handles audio file uploads for Streamlit applications.
    """
    
    def __init__(self, upload_dir: Optional[str] = None, max_size_mb: float = 100):
        """
        Initialize upload handler.
        
        Args:
            upload_dir: Directory to save uploaded files
            max_size_mb: Maximum upload size in MB
        """
        self.upload_dir = Path(upload_dir) if upload_dir else Path("temp/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self.validator = AudioValidator()
    
    def save_upload(
        self,
        file_content: bytes,
        file_name: str,
        validate: bool = True
    ) -> Tuple[bool, str, Optional[ValidationResult]]:
        """
        Save uploaded file to disk.
        
        Args:
            file_content: Raw file bytes
            file_name: Original filename
            validate: Whether to validate before saving
            
        Returns:
            Tuple of (success, file_path or error message, validation result)
        """
        validation_result = None
        
        if validate:
            validation_result = self.validator.validate_upload(
                file_content, file_name, self.max_size_mb
            )
            if not validation_result.is_valid:
                return False, "; ".join(validation_result.errors), validation_result
        
        # Generate unique filename
        safe_name = self._sanitize_filename(file_name)
        output_path = self.upload_dir / safe_name
        
        # Handle duplicates
        counter = 1
        while output_path.exists():
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            output_path = self.upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Save file
        try:
            with open(output_path, 'wb') as f:
                f.write(file_content)
            return True, str(output_path), validation_result
        except Exception as e:
            return False, f"Failed to save file: {str(e)}", validation_result
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path separators and dangerous characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Ensure it has a valid extension
        if '.' not in sanitized:
            sanitized += '.audio'
        
        return sanitized
    
    def cleanup_old_uploads(self, max_age_hours: int = 24) -> int:
        """
        Remove old uploaded files.
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Number of files removed
        """
        import time
        
        removed = 0
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        removed += 1
                    except Exception:
                        pass
        
        return removed
