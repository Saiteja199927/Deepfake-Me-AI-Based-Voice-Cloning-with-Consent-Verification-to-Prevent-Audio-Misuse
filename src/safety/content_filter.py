"""
Content Filter Module
Filters harmful, inappropriate, or prohibited text content before TTS synthesis
"""

import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class FilterCategory(Enum):
    """Categories of filtered content."""
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SEXUAL_CONTENT = "sexual_content"
    SELF_HARM = "self_harm"
    HARASSMENT = "harassment"
    PROFANITY = "profanity"
    PERSONAL_INFO = "personal_info"
    IMPERSONATION = "impersonation"
    SPAM = "spam"
    CUSTOM = "custom"


class FilterSeverity(Enum):
    """Severity levels for filtered content."""
    LOW = "low"          # Warning, still allowed
    MEDIUM = "medium"    # Requires review/confirmation
    HIGH = "high"        # Blocked automatically
    CRITICAL = "critical"  # Blocked and logged for review


@dataclass
class ContentFilterResult:
    """Result of content filtering."""
    is_safe: bool
    original_text: str
    filtered_text: str
    flags: List[Dict[str, Any]] = field(default_factory=list)
    categories_detected: List[FilterCategory] = field(default_factory=list)
    severity: FilterSeverity = FilterSeverity.LOW
    confidence: float = 1.0
    requires_review: bool = False
    blocked: bool = False
    sanitized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_safe': self.is_safe,
            'original_text': self.original_text,
            'filtered_text': self.filtered_text,
            'flags': self.flags,
            'categories_detected': [c.value for c in self.categories_detected],
            'severity': self.severity.value,
            'confidence': self.confidence,
            'requires_review': self.requires_review,
            'blocked': self.blocked,
            'sanitized': self.sanitized,
            'metadata': self.metadata
        }


class ContentFilter:
    """
    Content filtering system for TTS text input.
    
    Features:
    - Multi-category harmful content detection
    - Personal information filtering (PII)
    - Profanity filtering with severity levels
    - Custom blocklist/allowlist support
    - Configurable sensitivity levels
    """
    
    # Built-in profanity patterns (partial list, expand as needed)
    PROFANITY_PATTERNS = [
        r'\b(f+u+c+k+|sh+i+t+|a+ss+|damn+|hell+|bitch+|crap+)\b',
        r'\b(bastard|asshole|dumbass|jackass)\b',
    ]
    
    # Hate speech indicators (keywords that need context)
    HATE_SPEECH_INDICATORS = [
        r'\b(kill\s+all|death\s+to|exterminate)\b',
        r'\b(hate|destroy)\s+(all\s+)?(jews|muslims|christians|blacks|whites|gays|women|men)\b',
    ]
    
    # Violence patterns
    VIOLENCE_PATTERNS = [
        r'\b(kill|murder|assassinate|bomb|shoot|stab)\s+(you|him|her|them|everyone)\b',
        r'\b(how\s+to\s+(make|build)\s+(a\s+)?(bomb|weapon|gun))\b',
        r'\b(terrorist|terrorism)\b',
    ]
    
    # Self-harm patterns
    SELF_HARM_PATTERNS = [
        r'\b(kill\s+(myself|yourself)|suicide|self.?harm)\b',
        r'\b(want\s+to\s+die|end\s+(my|your)\s+life)\b',
    ]
    
    # Personal Information patterns (PII)
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'ssn': r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }
    
    # Impersonation indicators
    IMPERSONATION_PATTERNS = [
        r'\b(i\s+am|this\s+is)\s+(president|prime\s+minister|ceo|doctor|police|fbi|cia)\b',
        r'\b(speaking\s+as|on\s+behalf\s+of)\s+(the\s+)?(government|police|official)\b',
    ]
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        sensitivity: str = "medium",
        enable_pii_filter: bool = True,
        enable_profanity_filter: bool = True,
        custom_blocklist: Optional[List[str]] = None,
        custom_allowlist: Optional[List[str]] = None
    ):
        """
        Initialize Content Filter.
        
        Args:
            config_path: Path to custom configuration file
            sensitivity: Sensitivity level ('low', 'medium', 'high')
            enable_pii_filter: Whether to filter personal information
            enable_profanity_filter: Whether to filter profanity
            custom_blocklist: Additional words/phrases to block
            custom_allowlist: Words/phrases to always allow
        """
        self.sensitivity = sensitivity
        self.enable_pii_filter = enable_pii_filter
        self.enable_profanity_filter = enable_profanity_filter
        
        # Custom lists
        self.blocklist: Set[str] = set(custom_blocklist or [])
        self.allowlist: Set[str] = set(custom_allowlist or [])
        
        # Load config if provided
        if config_path:
            self._load_config(config_path)
        
        # Compile regex patterns for performance
        self._compile_patterns()
        
        # Statistics
        self._filter_stats = {
            'total_checked': 0,
            'total_blocked': 0,
            'total_sanitized': 0,
            'categories': {cat.value: 0 for cat in FilterCategory}
        }
    
    def _load_config(self, config_path: str) -> None:
        """Load configuration from file."""
        path = Path(config_path)
        if path.exists():
            with open(path, 'r') as f:
                config = json.load(f)
                self.blocklist.update(config.get('blocklist', []))
                self.allowlist.update(config.get('allowlist', []))
                self.sensitivity = config.get('sensitivity', self.sensitivity)
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        flags = re.IGNORECASE
        
        self._profanity_regex = [re.compile(p, flags) for p in self.PROFANITY_PATTERNS]
        self._hate_regex = [re.compile(p, flags) for p in self.HATE_SPEECH_INDICATORS]
        self._violence_regex = [re.compile(p, flags) for p in self.VIOLENCE_PATTERNS]
        self._self_harm_regex = [re.compile(p, flags) for p in self.SELF_HARM_PATTERNS]
        self._impersonation_regex = [re.compile(p, flags) for p in self.IMPERSONATION_PATTERNS]
        self._pii_regex = {k: re.compile(v, flags) for k, v in self.PII_PATTERNS.items()}
    
    def filter(self, text: str, sanitize: bool = True) -> ContentFilterResult:
        """
        Filter text content for harmful or inappropriate material.
        
        Args:
            text: Input text to filter
            sanitize: Whether to sanitize (replace) flagged content
            
        Returns:
            ContentFilterResult with filtering results
        """
        self._filter_stats['total_checked'] += 1
        
        flags = []
        categories = []
        filtered_text = text
        max_severity = FilterSeverity.LOW
        blocked = False
        requires_review = False
        
        # Check allowlist first
        if self._is_in_allowlist(text):
            return ContentFilterResult(
                is_safe=True,
                original_text=text,
                filtered_text=text,
                confidence=1.0,
                metadata={'allowlisted': True}
            )
        
        # Check custom blocklist
        blocklist_match = self._check_blocklist(text)
        if blocklist_match:
            flags.append({
                'type': 'blocklist',
                'matches': blocklist_match,
                'severity': 'high'
            })
            categories.append(FilterCategory.CUSTOM)
            max_severity = FilterSeverity.HIGH
        
        # Check profanity
        if self.enable_profanity_filter:
            profanity_flags = self._check_profanity(text)
            if profanity_flags:
                flags.extend(profanity_flags)
                categories.append(FilterCategory.PROFANITY)
                if sanitize:
                    filtered_text = self._sanitize_profanity(filtered_text)
                if self.sensitivity == 'high':
                    max_severity = max(max_severity, FilterSeverity.MEDIUM, key=lambda x: list(FilterSeverity).index(x))
        
        # Check hate speech
        hate_flags = self._check_patterns(text, self._hate_regex, FilterCategory.HATE_SPEECH)
        if hate_flags:
            flags.extend(hate_flags)
            categories.append(FilterCategory.HATE_SPEECH)
            max_severity = FilterSeverity.CRITICAL
            blocked = True
        
        # Check violence
        violence_flags = self._check_patterns(text, self._violence_regex, FilterCategory.VIOLENCE)
        if violence_flags:
            flags.extend(violence_flags)
            categories.append(FilterCategory.VIOLENCE)
            max_severity = max(max_severity, FilterSeverity.HIGH, key=lambda x: list(FilterSeverity).index(x))
            if self.sensitivity != 'low':
                blocked = True
        
        # Check self-harm
        self_harm_flags = self._check_patterns(text, self._self_harm_regex, FilterCategory.SELF_HARM)
        if self_harm_flags:
            flags.extend(self_harm_flags)
            categories.append(FilterCategory.SELF_HARM)
            max_severity = FilterSeverity.CRITICAL
            blocked = True
            requires_review = True
        
        # Check impersonation
        impersonation_flags = self._check_patterns(text, self._impersonation_regex, FilterCategory.IMPERSONATION)
        if impersonation_flags:
            flags.extend(impersonation_flags)
            categories.append(FilterCategory.IMPERSONATION)
            max_severity = max(max_severity, FilterSeverity.MEDIUM, key=lambda x: list(FilterSeverity).index(x))
            requires_review = True
        
        # Check PII
        if self.enable_pii_filter:
            pii_flags = self._check_pii(text)
            if pii_flags:
                flags.extend(pii_flags)
                categories.append(FilterCategory.PERSONAL_INFO)
                if sanitize:
                    filtered_text = self._sanitize_pii(filtered_text)
                max_severity = max(max_severity, FilterSeverity.MEDIUM, key=lambda x: list(FilterSeverity).index(x))
        
        # Update statistics
        if blocked:
            self._filter_stats['total_blocked'] += 1
        if filtered_text != text:
            self._filter_stats['total_sanitized'] += 1
        for cat in categories:
            self._filter_stats['categories'][cat.value] += 1
        
        is_safe = len(flags) == 0
        
        return ContentFilterResult(
            is_safe=is_safe,
            original_text=text,
            filtered_text=filtered_text if not blocked else "[CONTENT BLOCKED]",
            flags=flags,
            categories_detected=list(set(categories)),
            severity=max_severity,
            confidence=0.85 if flags else 1.0,
            requires_review=requires_review,
            blocked=blocked,
            sanitized=filtered_text != text,
            metadata={
                'sensitivity': self.sensitivity,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    
    def _is_in_allowlist(self, text: str) -> bool:
        """Check if text is in allowlist."""
        text_lower = text.lower()
        return any(allowed.lower() in text_lower for allowed in self.allowlist)
    
    def _check_blocklist(self, text: str) -> List[str]:
        """Check text against custom blocklist."""
        matches = []
        text_lower = text.lower()
        for blocked in self.blocklist:
            if blocked.lower() in text_lower:
                matches.append(blocked)
        return matches
    
    def _check_profanity(self, text: str) -> List[Dict[str, Any]]:
        """Check for profanity."""
        flags = []
        for regex in self._profanity_regex:
            matches = regex.findall(text)
            if matches:
                flags.append({
                    'type': 'profanity',
                    'matches': matches,
                    'severity': 'low' if self.sensitivity == 'low' else 'medium'
                })
        return flags
    
    def _check_patterns(
        self, 
        text: str, 
        patterns: List[re.Pattern], 
        category: FilterCategory
    ) -> List[Dict[str, Any]]:
        """Check text against a list of patterns."""
        flags = []
        for regex in patterns:
            matches = regex.findall(text)
            if matches:
                flags.append({
                    'type': category.value,
                    'matches': matches if isinstance(matches[0], str) else [m[0] if isinstance(m, tuple) else m for m in matches],
                    'severity': 'high'
                })
        return flags
    
    def _check_pii(self, text: str) -> List[Dict[str, Any]]:
        """Check for personal identifiable information."""
        flags = []
        for pii_type, regex in self._pii_regex.items():
            matches = regex.findall(text)
            if matches:
                flags.append({
                    'type': 'pii',
                    'pii_type': pii_type,
                    'count': len(matches),
                    'severity': 'medium'
                })
        return flags
    
    def _sanitize_profanity(self, text: str) -> str:
        """Replace profanity with asterisks."""
        for regex in self._profanity_regex:
            text = regex.sub(lambda m: '*' * len(m.group()), text)
        return text
    
    def _sanitize_pii(self, text: str) -> str:
        """Replace PII with placeholders."""
        for pii_type, regex in self._pii_regex.items():
            placeholder = f"[{pii_type.upper()}_REDACTED]"
            text = regex.sub(placeholder, text)
        return text
    
    def add_to_blocklist(self, words: List[str]) -> None:
        """Add words to blocklist."""
        self.blocklist.update(words)
    
    def add_to_allowlist(self, words: List[str]) -> None:
        """Add words to allowlist."""
        self.allowlist.update(words)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get filtering statistics."""
        return {
            **self._filter_stats,
            'blocklist_size': len(self.blocklist),
            'allowlist_size': len(self.allowlist),
            'sensitivity': self.sensitivity
        }
    
    def reset_statistics(self) -> None:
        """Reset filtering statistics."""
        self._filter_stats = {
            'total_checked': 0,
            'total_blocked': 0,
            'total_sanitized': 0,
            'categories': {cat.value: 0 for cat in FilterCategory}
        }
