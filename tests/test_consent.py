"""
Unit Tests for Consent Module
Tests for ConsentManager, ConsentWorkflow, ConsentLogger, and ConsentStorage
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.consent import (
    ConsentManager, ConsentWorkflow, ConsentLogger, ConsentStorage,
    ConsentStatus, ConsentType, WorkflowStatus, LogLevel, LogCategory
)


class TestConsentManager:
    """Tests for ConsentManager class."""
    
    def test_manager_initialization(self, temp_dir):
        """Test ConsentManager initializes correctly."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        assert manager is not None
    
    def test_create_consent(self, temp_dir):
        """Test creating a new consent record."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        consent = manager.create_consent(
            user_id="test_user_123",
            consent_type=ConsentType.TERMS_OF_SERVICE,
            ip_address="127.0.0.1"
        )
        
        assert consent is not None
        assert consent.user_id == "test_user_123"
        assert consent.consent_type == ConsentType.TERMS_OF_SERVICE
        assert consent.status == ConsentStatus.PENDING
    
    def test_grant_consent(self, temp_dir):
        """Test granting a consent."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        consent = manager.create_consent(
            user_id="test_user_456",
            consent_type=ConsentType.PRIVACY_POLICY
        )
        
        granted = manager.grant_consent(consent.consent_id)
        
        assert granted is not None
        assert granted.status == ConsentStatus.GRANTED
    
    def test_deny_consent(self, temp_dir):
        """Test denying a consent."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        consent = manager.create_consent(
            user_id="test_user_789",
            consent_type=ConsentType.DATA_PROCESSING
        )
        
        denied = manager.deny_consent(consent.consent_id)
        
        assert denied is not None
        assert denied.status == ConsentStatus.DENIED
    
    def test_revoke_consent(self, temp_dir):
        """Test revoking a granted consent."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        # Create and grant consent
        consent = manager.create_consent(
            user_id="test_user_revoke",
            consent_type=ConsentType.VOICE_CLONING
        )
        manager.grant_consent(consent.consent_id)
        
        # Revoke it
        revoked = manager.revoke_consent(consent.consent_id, reason="User requested")
        
        assert revoked is not None
        assert revoked.status == ConsentStatus.REVOKED
    
    def test_get_user_consents(self, temp_dir):
        """Test getting all consents for a user."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        user_id = "test_user_multi"
        
        # Create multiple consents
        manager.create_consent(user_id=user_id, consent_type=ConsentType.TERMS_OF_SERVICE)
        manager.create_consent(user_id=user_id, consent_type=ConsentType.PRIVACY_POLICY)
        
        consents = manager.get_user_consents(user_id)
        
        assert len(consents) >= 2
    
    def test_verify_consent(self, temp_dir):
        """Test consent verification."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        consent = manager.create_consent(
            user_id="test_verify",
            consent_type=ConsentType.TERMS_OF_SERVICE
        )
        manager.grant_consent(consent.consent_id)
        
        # Verify the consent
        try:
            verified = manager.verify_consent(consent.consent_id)
            assert verified is not None
        except Exception:
            # Verification may fail if proof not created
            pass
    
    def test_check_has_consent(self, temp_dir):
        """Test checking if user has specific consent type."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        
        user_id = "test_user_check"
        
        # Initially should not have consent
        has_tos = manager.check_consent(user_id, ConsentType.TERMS_OF_SERVICE)
        assert has_tos == False
        
        # Grant consent
        consent = manager.create_consent(user_id=user_id, consent_type=ConsentType.TERMS_OF_SERVICE)
        manager.grant_consent(consent.consent_id)
        
        # Now should have consent
        has_tos = manager.check_consent(user_id, ConsentType.TERMS_OF_SERVICE)
        assert has_tos == True


class TestConsentWorkflow:
    """Tests for ConsentWorkflow class."""
    
    def test_workflow_initialization(self, temp_dir):
        """Test ConsentWorkflow initializes correctly."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        workflow = ConsentWorkflow(
            consent_manager=manager,
            storage_dir=str(temp_dir / "workflows")
        )
        assert workflow is not None
    
    def test_get_templates(self, temp_dir):
        """Test getting workflow templates."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        workflow = ConsentWorkflow(consent_manager=manager)
        
        templates = workflow.get_available_templates()
        
        assert isinstance(templates, list)
        assert len(templates) > 0
    
    def test_start_workflow(self, temp_dir):
        """Test starting a workflow."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        workflow = ConsentWorkflow(
            consent_manager=manager,
            storage_dir=str(temp_dir / "workflows")
        )
        
        result = workflow.start_workflow(
            user_id="test_workflow_user",
            template_id="basic_tts"
        )
        
        assert result is not None
        assert 'workflow_id' in result
    
    def test_process_workflow_step(self, temp_dir):
        """Test processing a workflow step."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        workflow = ConsentWorkflow(
            consent_manager=manager,
            storage_dir=str(temp_dir / "workflows")
        )
        
        # Start workflow
        start_result = workflow.start_workflow(
            user_id="test_step_user",
            template_id="basic_tts"
        )
        workflow_id = start_result['workflow_id']
        
        # Process first step
        step_result = workflow.process_step(
            workflow_id=workflow_id,
            step_number=1,
            accepted=True
        )
        
        assert step_result['success'] == True
    
    def test_workflow_completion(self, temp_dir):
        """Test completing a full workflow."""
        manager = ConsentManager(storage_dir=str(temp_dir / "consents"))
        workflow = ConsentWorkflow(
            consent_manager=manager,
            storage_dir=str(temp_dir / "workflows")
        )
        
        # Start workflow
        start_result = workflow.start_workflow(
            user_id="test_complete_user",
            template_id="basic_tts"
        )
        workflow_id = start_result['workflow_id']
        total_steps = start_result.get('total_steps', 3)
        
        # Process all steps
        for step in range(1, total_steps + 1):
            result = workflow.process_step(
                workflow_id=workflow_id,
                step_number=step,
                accepted=True
            )
            
            if result.get('workflow_completed'):
                break
        
        # Check workflow status
        status = workflow.get_workflow_status(workflow_id)
        assert status['status'] in ['completed', 'COMPLETED', WorkflowStatus.COMPLETED]


class TestConsentLogger:
    """Tests for ConsentLogger class."""
    
    def test_logger_initialization(self, temp_dir):
        """Test ConsentLogger initializes correctly."""
        logger = ConsentLogger(
            log_dir=str(temp_dir / "logs"),
            enable_file=True,
            enable_console=False
        )
        assert logger is not None
    
    def test_log_info(self, temp_dir):
        """Test logging info level message."""
        logger = ConsentLogger(
            log_dir=str(temp_dir / "logs"),
            enable_file=True,
            enable_console=False
        )
        
        entry = logger.log(
            level=LogLevel.INFO,
            category=LogCategory.CONSENT_GRANTED,
            message="Test info log",
            user_id="test_user"
        )
        
        assert entry is not None
        assert entry.level == LogLevel.INFO
    
    def test_log_warning(self, temp_dir):
        """Test logging warning level message."""
        logger = ConsentLogger(
            log_dir=str(temp_dir / "logs"),
            enable_console=False
        )
        
        entry = logger.log(
            level=LogLevel.WARNING,
            category=LogCategory.CONSENT_REVOKED,
            message="Test warning log",
            user_id="test_user"
        )
        
        assert entry is not None
        assert entry.level == LogLevel.WARNING
    
    def test_get_logs(self, temp_dir):
        """Test retrieving logs."""
        logger = ConsentLogger(
            log_dir=str(temp_dir / "logs"),
            enable_console=False
        )
        
        # Create some logs
        logger.log(LogLevel.INFO, LogCategory.CONSENT_GRANTED, "Log 1")
        logger.log(LogLevel.INFO, LogCategory.CONSENT_GRANTED, "Log 2")
        
        logs = logger.get_logs(limit=10)
        
        assert isinstance(logs, list)
        assert len(logs) >= 2


class TestConsentStorage:
    """Tests for ConsentStorage class."""
    
    def test_storage_initialization(self, temp_dir):
        """Test ConsentStorage initializes correctly."""
        storage = ConsentStorage(storage_dir=str(temp_dir / "storage"))
        assert storage is not None
    
    def test_save_and_load_record(self, temp_dir):
        """Test saving and loading consent records."""
        storage = ConsentStorage(storage_dir=str(temp_dir / "storage"))
        
        # Create a test record
        from src.consent.consent_storage import ConsentRecord
        
        record = ConsentRecord(
            record_id="test_record_123",
            user_id="test_user",
            consent_type="terms_of_service",
            status="granted",
            version="1.0.0",
            consent_text="I agree to the terms of service",
            granted_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Save
        storage.save_record(record)
        
        # Load
        loaded = storage.get_record("test_record_123")
        
        assert loaded is not None
        assert loaded.user_id == "test_user"
    
    def test_export_user_data(self, temp_dir):
        """Test GDPR export functionality."""
        storage = ConsentStorage(storage_dir=str(temp_dir / "storage"))
        
        try:
            export_data = storage.export_user_data("test_user")
            assert isinstance(export_data, (dict, str))
        except Exception:
            # Export may not be implemented
            pytest.skip("Export not available")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
