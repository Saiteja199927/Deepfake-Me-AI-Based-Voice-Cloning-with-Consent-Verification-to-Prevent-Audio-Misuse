"""
Consent Manager Module
Core consent management functionality for voice applications
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
import secrets


class ConsentStatus(Enum):
    """Status of a consent record."""
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ConsentType(Enum):
    """Types of consent required for voice applications."""
    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    VOICE_RECORDING = "voice_recording"
    VOICE_CLONING = "voice_cloning"
    DATA_PROCESSING = "data_processing"
    THIRD_PARTY_SHARING = "third_party_sharing"
    COMMERCIAL_USE = "commercial_use"
    RESEARCH_USE = "research_use"


@dataclass
class ConsentProof:
    """Cryptographic proof of consent."""
    proof_id: str
    consent_id: str
    timestamp: str
    hash_algorithm: str
    content_hash: str
    signature: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsentProof':
        return cls(**data)


@dataclass
class Consent:
    """Individual consent record."""
    consent_id: str
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    version: str
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    consent_text: str = ""
    additional_data: Dict[str, Any] = field(default_factory=dict)
    proof: Optional[ConsentProof] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            'consent_id': self.consent_id,
            'user_id': self.user_id,
            'consent_type': self.consent_type.value,
            'status': self.status.value,
            'version': self.version,
            'granted_at': self.granted_at,
            'expires_at': self.expires_at,
            'revoked_at': self.revoked_at,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'consent_text': self.consent_text,
            'additional_data': self.additional_data,
            'proof': self.proof.to_dict() if self.proof else None
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Consent':
        data['consent_type'] = ConsentType(data['consent_type'])
        data['status'] = ConsentStatus(data['status'])
        if data.get('proof'):
            data['proof'] = ConsentProof.from_dict(data['proof'])
        return cls(**data)


class ConsentManager:
    """
    Manages consent records with cryptographic proofs and audit trails.
    """
    
    # Consent text templates
    CONSENT_TEMPLATES = {
        ConsentType.TERMS_OF_SERVICE: {
            "title": "Terms of Service",
            "version": "1.0.0",
            "text": """By using this Voice TTS application, you agree to:
            
1. Use the service only for lawful purposes
2. Not attempt to clone voices without proper authorization
3. Not use generated audio for deceptive purposes
4. Comply with all applicable laws and regulations
5. Accept that the service is provided "as is" without warranties

Do you agree to these Terms of Service?"""
        },
        ConsentType.PRIVACY_POLICY: {
            "title": "Privacy Policy",
            "version": "1.0.0",
            "text": """We collect and process the following data:

1. **Voice Samples**: Audio recordings you upload for processing
2. **Usage Data**: How you interact with our application
3. **Technical Data**: Device info, IP address, browser type

Your data is:
- Processed securely using encryption
- Not shared with third parties without consent
- Deleted upon your request

Do you agree to our Privacy Policy?"""
        },
        ConsentType.VOICE_RECORDING: {
            "title": "Voice Recording Consent",
            "version": "1.0.0",
            "text": """I consent to having my voice recorded for:

1. Voice sample processing and analysis
2. Text-to-speech synthesis
3. Quality improvement of the service

I understand that:
- My recordings will be stored securely
- I can request deletion at any time
- Recordings may be processed by AI systems

Do you consent to voice recording?"""
        },
        ConsentType.VOICE_CLONING: {
            "title": "Voice Cloning Authorization",
            "version": "1.0.0",
            "text": """⚠️ IMPORTANT: Voice Cloning Consent

I hereby authorize the creation of a synthetic voice model based on my voice samples.

I confirm that:
1. I am the owner of the voice being cloned, OR
2. I have explicit written permission from the voice owner

I understand that:
- The cloned voice can generate speech from any text
- I am responsible for how the cloned voice is used
- Misuse may have legal consequences

Do you authorize voice cloning?"""
        },
        ConsentType.DATA_PROCESSING: {
            "title": "Data Processing Consent",
            "version": "1.0.0",
            "text": """I consent to the processing of my data including:

1. Audio files I upload
2. Text inputs I provide
3. Generated audio outputs
4. Usage patterns and preferences

Processing purposes:
- Providing the TTS service
- Improving audio quality
- Personalizing your experience

Do you consent to data processing?"""
        },
        ConsentType.COMMERCIAL_USE: {
            "title": "Commercial Use Authorization",
            "version": "1.0.0",
            "text": """I authorize the use of generated audio for commercial purposes:

1. Marketing and advertising materials
2. Commercial products and services
3. Monetized content creation
4. Business communications

I understand that commercial use may be subject to additional terms.

Do you authorize commercial use?"""
        }
    }
    
    def __init__(
        self, 
        storage_dir: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize the Consent Manager.
        
        Args:
            storage_dir: Directory to store consent records
            secret_key: Secret key for signing proofs (generated if not provided)
        """
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/consents")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Secret key for HMAC signatures
        self.secret_key = secret_key or self._load_or_create_secret_key()
        
        # In-memory cache of consents
        self._consent_cache: Dict[str, Consent] = {}
        
        # Load existing consents
        self._load_consents()
    
    def _load_or_create_secret_key(self) -> str:
        """Load or create a secret key for signing."""
        key_file = self.storage_dir / ".secret_key"
        if key_file.exists():
            return key_file.read_text().strip()
        else:
            key = secrets.token_hex(32)
            key_file.write_text(key)
            return key
    
    def _load_consents(self) -> None:
        """Load existing consent records from storage."""
        consents_file = self.storage_dir / "consents.json"
        if consents_file.exists():
            try:
                data = json.loads(consents_file.read_text())
                for consent_data in data.get('consents', []):
                    consent = Consent.from_dict(consent_data)
                    self._consent_cache[consent.consent_id] = consent
            except Exception as e:
                print(f"Error loading consents: {e}")
    
    def _save_consents(self) -> None:
        """Save consent records to storage."""
        consents_file = self.storage_dir / "consents.json"
        data = {
            'version': '1.0.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'consents': [c.to_dict() for c in self._consent_cache.values()]
        }
        consents_file.write_text(json.dumps(data, indent=2))
    
    def create_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Consent:
        """
        Create a new pending consent record.
        
        Args:
            user_id: Unique user identifier
            consent_type: Type of consent
            ip_address: User's IP address
            user_agent: User's browser/client info
            additional_data: Any additional metadata
            
        Returns:
            New Consent object with pending status
        """
        template = self.CONSENT_TEMPLATES.get(consent_type, {})
        
        consent = Consent(
            consent_id=str(uuid.uuid4()),
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.PENDING,
            version=template.get('version', '1.0.0'),
            consent_text=template.get('text', ''),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data or {}
        )
        
        self._consent_cache[consent.consent_id] = consent
        self._save_consents()
        
        return consent
    
    def grant_consent(
        self,
        consent_id: str,
        expires_in_days: Optional[int] = None
    ) -> Consent:
        """
        Grant a pending consent.
        
        Args:
            consent_id: ID of the consent to grant
            expires_in_days: Optional expiration in days
            
        Returns:
            Updated Consent object
        """
        consent = self._consent_cache.get(consent_id)
        if not consent:
            raise ValueError(f"Consent not found: {consent_id}")
        
        if consent.status != ConsentStatus.PENDING:
            raise ValueError(f"Consent is not pending: {consent.status.value}")
        
        now = datetime.now(timezone.utc)
        consent.status = ConsentStatus.GRANTED
        consent.granted_at = now.isoformat()
        
        if expires_in_days:
            from datetime import timedelta
            consent.expires_at = (now + timedelta(days=expires_in_days)).isoformat()
        
        # Generate cryptographic proof
        consent.proof = self._generate_proof(consent)
        
        self._save_consents()
        
        return consent
    
    def deny_consent(self, consent_id: str) -> Consent:
        """
        Deny a pending consent.
        
        Args:
            consent_id: ID of the consent to deny
            
        Returns:
            Updated Consent object
        """
        consent = self._consent_cache.get(consent_id)
        if not consent:
            raise ValueError(f"Consent not found: {consent_id}")
        
        consent.status = ConsentStatus.DENIED
        self._save_consents()
        
        return consent
    
    def revoke_consent(self, consent_id: str, reason: Optional[str] = None) -> Consent:
        """
        Revoke a previously granted consent.
        
        Args:
            consent_id: ID of the consent to revoke
            reason: Optional reason for revocation
            
        Returns:
            Updated Consent object
        """
        consent = self._consent_cache.get(consent_id)
        if not consent:
            raise ValueError(f"Consent not found: {consent_id}")
        
        if consent.status != ConsentStatus.GRANTED:
            raise ValueError(f"Cannot revoke consent with status: {consent.status.value}")
        
        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.now(timezone.utc).isoformat()
        consent.additional_data['revocation_reason'] = reason
        
        self._save_consents()
        
        return consent
    
    def check_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if a user has granted a specific type of consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to check
            
        Returns:
            True if valid consent exists
        """
        for consent in self._consent_cache.values():
            if consent.user_id == user_id and consent.consent_type == consent_type:
                if consent.status == ConsentStatus.GRANTED:
                    # Check expiration
                    if consent.expires_at:
                        expires = datetime.fromisoformat(consent.expires_at)
                        if datetime.now(timezone.utc) > expires:
                            consent.status = ConsentStatus.EXPIRED
                            self._save_consents()
                            return False
                    return True
        return False
    
    def get_user_consents(self, user_id: str) -> List[Consent]:
        """
        Get all consents for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of Consent objects
        """
        return [c for c in self._consent_cache.values() if c.user_id == user_id]
    
    def get_consent(self, consent_id: str) -> Optional[Consent]:
        """Get a specific consent by ID."""
        return self._consent_cache.get(consent_id)
    
    def get_consent_template(self, consent_type: ConsentType) -> Dict[str, Any]:
        """Get the template for a consent type."""
        return self.CONSENT_TEMPLATES.get(consent_type, {})
    
    def _generate_proof(self, consent: Consent) -> ConsentProof:
        """
        Generate a cryptographic proof of consent.
        
        Args:
            consent: Consent object to generate proof for
            
        Returns:
            ConsentProof object
        """
        # Create content to hash
        content = {
            'consent_id': consent.consent_id,
            'user_id': consent.user_id,
            'consent_type': consent.consent_type.value,
            'version': consent.version,
            'granted_at': consent.granted_at,
            'consent_text': consent.consent_text
        }
        content_json = json.dumps(content, sort_keys=True)
        
        # Generate content hash
        content_hash = hashlib.sha256(content_json.encode()).hexdigest()
        
        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            content_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return ConsentProof(
            proof_id=str(uuid.uuid4()),
            consent_id=consent.consent_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            hash_algorithm='SHA-256',
            content_hash=content_hash,
            signature=signature,
            metadata={
                'ip_address': consent.ip_address,
                'user_agent': consent.user_agent
            }
        )
    
    def verify_proof(self, consent: Consent) -> bool:
        """
        Verify the cryptographic proof of a consent.
        
        Args:
            consent: Consent with proof to verify
            
        Returns:
            True if proof is valid
        """
        if not consent.proof:
            return False
        
        # Recreate content hash
        content = {
            'consent_id': consent.consent_id,
            'user_id': consent.user_id,
            'consent_type': consent.consent_type.value,
            'version': consent.version,
            'granted_at': consent.granted_at,
            'consent_text': consent.consent_text
        }
        content_json = json.dumps(content, sort_keys=True)
        expected_hash = hashlib.sha256(content_json.encode()).hexdigest()
        
        # Verify hash matches
        if consent.proof.content_hash != expected_hash:
            return False
        
        # Verify signature
        expected_signature = hmac.new(
            self.secret_key.encode(),
            expected_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(consent.proof.signature, expected_signature)
    
    def export_consent_proof(self, consent_id: str) -> Dict[str, Any]:
        """
        Export a consent proof for external verification.
        
        Args:
            consent_id: ID of the consent
            
        Returns:
            Dictionary with exportable proof data
        """
        consent = self.get_consent(consent_id)
        if not consent or not consent.proof:
            raise ValueError("Consent or proof not found")
        
        return {
            'consent': consent.to_dict(),
            'verification_status': 'valid' if self.verify_proof(consent) else 'invalid',
            'exported_at': datetime.now(timezone.utc).isoformat()
        }
