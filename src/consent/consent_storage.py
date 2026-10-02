"""
Consent Storage Module
Persistent storage for consent records with proof management
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class ConsentRecord:
    """Complete consent record with all metadata."""
    record_id: str
    user_id: str
    consent_type: str
    status: str
    version: str
    consent_text: str
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    revoked_at: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    proof_hash: Optional[str] = None
    proof_signature: Optional[str] = None
    workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsentRecord':
        return cls(**data)


class ConsentStorage:
    """
    Persistent storage manager for consent records.
    Handles saving, loading, querying, and exporting consent data.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize consent storage.
        
        Args:
            storage_dir: Directory for storing consent data
        """
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/consent_storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage files
        self.records_file = self.storage_dir / "consent_records.json"
        self.proofs_dir = self.storage_dir / "proofs"
        self.proofs_dir.mkdir(exist_ok=True)
        
        # In-memory cache
        self._records: Dict[str, ConsentRecord] = {}
        
        # Load existing records
        self._load_records()
    
    def _load_records(self) -> None:
        """Load records from storage."""
        if self.records_file.exists():
            try:
                data = json.loads(self.records_file.read_text())
                for record_data in data.get('records', []):
                    record = ConsentRecord.from_dict(record_data)
                    self._records[record.record_id] = record
            except Exception as e:
                print(f"Error loading consent records: {e}")
    
    def _save_records(self) -> None:
        """Save records to storage."""
        data = {
            'version': '1.0.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'total_records': len(self._records),
            'records': [r.to_dict() for r in self._records.values()]
        }
        self.records_file.write_text(json.dumps(data, indent=2))
    
    def save_record(self, record: ConsentRecord) -> str:
        """
        Save a consent record.
        
        Args:
            record: ConsentRecord to save
            
        Returns:
            Record ID
        """
        record.updated_at = datetime.now(timezone.utc).isoformat()
        self._records[record.record_id] = record
        self._save_records()
        return record.record_id
    
    def get_record(self, record_id: str) -> Optional[ConsentRecord]:
        """Get a record by ID."""
        return self._records.get(record_id)
    
    def get_user_records(self, user_id: str) -> List[ConsentRecord]:
        """Get all records for a user."""
        return [r for r in self._records.values() if r.user_id == user_id]
    
    def get_records_by_type(self, consent_type: str) -> List[ConsentRecord]:
        """Get all records of a specific type."""
        return [r for r in self._records.values() if r.consent_type == consent_type]
    
    def get_active_records(self, user_id: str) -> List[ConsentRecord]:
        """Get active (granted, non-expired) records for a user."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            r for r in self._records.values()
            if r.user_id == user_id 
            and r.status == 'granted'
            and (not r.expires_at or r.expires_at > now)
        ]
    
    def update_record_status(self, record_id: str, status: str) -> bool:
        """Update record status."""
        record = self._records.get(record_id)
        if not record:
            return False
        
        record.status = status
        record.updated_at = datetime.now(timezone.utc).isoformat()
        
        if status == 'revoked':
            record.revoked_at = record.updated_at
        
        self._save_records()
        return True
    
    def delete_record(self, record_id: str) -> bool:
        """Delete a record (for GDPR compliance)."""
        if record_id in self._records:
            del self._records[record_id]
            self._save_records()
            return True
        return False
    
    def delete_user_data(self, user_id: str) -> int:
        """Delete all records for a user (GDPR right to be forgotten)."""
        records_to_delete = [r.record_id for r in self._records.values() if r.user_id == user_id]
        for record_id in records_to_delete:
            del self._records[record_id]
        self._save_records()
        return len(records_to_delete)
    
    def save_proof(self, record_id: str, proof_data: Dict[str, Any]) -> str:
        """
        Save consent proof to separate file.
        
        Args:
            record_id: Associated record ID
            proof_data: Proof data to save
            
        Returns:
            Path to proof file
        """
        proof_file = self.proofs_dir / f"{record_id}_proof.json"
        proof_data['saved_at'] = datetime.now(timezone.utc).isoformat()
        proof_file.write_text(json.dumps(proof_data, indent=2))
        return str(proof_file)
    
    def get_proof(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get proof for a record."""
        proof_file = self.proofs_dir / f"{record_id}_proof.json"
        if proof_file.exists():
            return json.loads(proof_file.read_text())
        return None
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all data for a user (GDPR data portability).
        
        Args:
            user_id: User ID to export data for
            
        Returns:
            Dictionary with all user consent data
        """
        records = self.get_user_records(user_id)
        
        export_data = {
            'export_date': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'total_records': len(records),
            'records': [],
        }
        
        for record in records:
            record_data = record.to_dict()
            proof = self.get_proof(record.record_id)
            if proof:
                record_data['proof'] = proof
            export_data['records'].append(record_data)
        
        return export_data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        records = list(self._records.values())
        
        status_counts = {}
        type_counts = {}
        
        for record in records:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
            type_counts[record.consent_type] = type_counts.get(record.consent_type, 0) + 1
        
        return {
            'total_records': len(records),
            'unique_users': len(set(r.user_id for r in records)),
            'by_status': status_counts,
            'by_type': type_counts,
            'storage_path': str(self.storage_dir)
        }
    
    def search_records(
        self,
        user_id: Optional[str] = None,
        consent_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[ConsentRecord]:
        """
        Search records with filters.
        
        Args:
            user_id: Filter by user ID
            consent_type: Filter by consent type
            status: Filter by status
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            
        Returns:
            List of matching records
        """
        results = list(self._records.values())
        
        if user_id:
            results = [r for r in results if r.user_id == user_id]
        if consent_type:
            results = [r for r in results if r.consent_type == consent_type]
        if status:
            results = [r for r in results if r.status == status]
        if start_date:
            results = [r for r in results if r.created_at >= start_date]
        if end_date:
            results = [r for r in results if r.created_at <= end_date]
        
        return results
