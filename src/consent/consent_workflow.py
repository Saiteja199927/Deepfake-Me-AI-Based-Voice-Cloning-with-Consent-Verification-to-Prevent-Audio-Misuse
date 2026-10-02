"""
Consent Workflow Module
Multi-step consent workflow management
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict

from .consent_manager import ConsentManager, ConsentType, ConsentStatus


class WorkflowStatus(Enum):
    """Status of a consent workflow."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class WorkflowStep:
    """Individual step in a consent workflow."""
    step_id: str
    step_number: int
    consent_type: ConsentType
    title: str
    description: str
    required: bool = True
    status: ConsentStatus = ConsentStatus.PENDING
    consent_id: Optional[str] = None
    completed_at: Optional[str] = None
    skipped: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'step_id': self.step_id,
            'step_number': self.step_number,
            'consent_type': self.consent_type.value,
            'title': self.title,
            'description': self.description,
            'required': self.required,
            'status': self.status.value,
            'consent_id': self.consent_id,
            'completed_at': self.completed_at,
            'skipped': self.skipped
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        data['consent_type'] = ConsentType(data['consent_type'])
        data['status'] = ConsentStatus(data['status'])
        return cls(**data)


@dataclass
class WorkflowState:
    """State of a consent workflow session."""
    workflow_id: str
    user_id: str
    workflow_type: str
    status: WorkflowStatus
    current_step: int
    total_steps: int
    steps: List[WorkflowStep]
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'workflow_id': self.workflow_id,
            'user_id': self.user_id,
            'workflow_type': self.workflow_type,
            'status': self.status.value,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'steps': [s.to_dict() for s in self.steps],
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_at': self.completed_at,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        data['status'] = WorkflowStatus(data['status'])
        data['steps'] = [WorkflowStep.from_dict(s) for s in data['steps']]
        return cls(**data)


class ConsentWorkflow:
    """
    Manages multi-step consent workflows for voice applications.
    """
    
    # Predefined workflow templates
    WORKFLOW_TEMPLATES = {
        'basic_tts': {
            'name': 'Basic TTS Usage',
            'description': 'Standard consent flow for text-to-speech features',
            'steps': [
                {
                    'consent_type': ConsentType.TERMS_OF_SERVICE,
                    'title': 'Terms of Service',
                    'description': 'Review and accept our terms of service',
                    'required': True
                },
                {
                    'consent_type': ConsentType.PRIVACY_POLICY,
                    'title': 'Privacy Policy',
                    'description': 'Review and accept our privacy policy',
                    'required': True
                },
                {
                    'consent_type': ConsentType.DATA_PROCESSING,
                    'title': 'Data Processing',
                    'description': 'Consent to data processing for TTS services',
                    'required': True
                }
            ]
        },
        'voice_recording': {
            'name': 'Voice Recording Consent',
            'description': 'Consent flow for recording voice samples',
            'steps': [
                {
                    'consent_type': ConsentType.TERMS_OF_SERVICE,
                    'title': 'Terms of Service',
                    'description': 'Review and accept our terms of service',
                    'required': True
                },
                {
                    'consent_type': ConsentType.PRIVACY_POLICY,
                    'title': 'Privacy Policy',
                    'description': 'Review and accept our privacy policy',
                    'required': True
                },
                {
                    'consent_type': ConsentType.VOICE_RECORDING,
                    'title': 'Voice Recording Authorization',
                    'description': 'Authorize recording of your voice',
                    'required': True
                },
                {
                    'consent_type': ConsentType.DATA_PROCESSING,
                    'title': 'Data Processing',
                    'description': 'Consent to processing of voice data',
                    'required': True
                }
            ]
        },
        'voice_cloning': {
            'name': 'Voice Cloning Authorization',
            'description': 'Complete consent flow for voice cloning features',
            'steps': [
                {
                    'consent_type': ConsentType.TERMS_OF_SERVICE,
                    'title': 'Terms of Service',
                    'description': 'Review and accept our terms of service',
                    'required': True
                },
                {
                    'consent_type': ConsentType.PRIVACY_POLICY,
                    'title': 'Privacy Policy',
                    'description': 'Review and accept our privacy policy',
                    'required': True
                },
                {
                    'consent_type': ConsentType.VOICE_RECORDING,
                    'title': 'Voice Recording Authorization',
                    'description': 'Authorize recording of your voice',
                    'required': True
                },
                {
                    'consent_type': ConsentType.VOICE_CLONING,
                    'title': 'Voice Cloning Consent',
                    'description': 'Authorize creation of a synthetic voice',
                    'required': True
                },
                {
                    'consent_type': ConsentType.DATA_PROCESSING,
                    'title': 'Data Processing',
                    'description': 'Consent to AI processing of voice data',
                    'required': True
                },
                {
                    'consent_type': ConsentType.COMMERCIAL_USE,
                    'title': 'Commercial Use (Optional)',
                    'description': 'Allow commercial use of generated content',
                    'required': False
                }
            ]
        }
    }
    
    def __init__(
        self,
        consent_manager: ConsentManager,
        storage_dir: Optional[str] = None
    ):
        """
        Initialize the Consent Workflow manager.
        
        Args:
            consent_manager: ConsentManager instance
            storage_dir: Directory to store workflow states
        """
        self.consent_manager = consent_manager
        self.storage_dir = Path(storage_dir) if storage_dir else Path("data/workflows")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Active workflows cache
        self._workflows: Dict[str, WorkflowState] = {}
        
        # Load existing workflows
        self._load_workflows()
    
    def _load_workflows(self) -> None:
        """Load existing workflow states from storage."""
        workflows_file = self.storage_dir / "workflows.json"
        if workflows_file.exists():
            try:
                data = json.loads(workflows_file.read_text())
                for workflow_data in data.get('workflows', []):
                    workflow = WorkflowState.from_dict(workflow_data)
                    self._workflows[workflow.workflow_id] = workflow
            except Exception as e:
                print(f"Error loading workflows: {e}")
    
    def _save_workflows(self) -> None:
        """Save workflow states to storage."""
        workflows_file = self.storage_dir / "workflows.json"
        data = {
            'version': '1.0.0',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'workflows': [w.to_dict() for w in self._workflows.values()]
        }
        workflows_file.write_text(json.dumps(data, indent=2))
    
    def get_available_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available workflow templates."""
        return {
            key: {
                'name': template['name'],
                'description': template['description'],
                'step_count': len(template['steps']),
                'required_consents': [
                    s['consent_type'].value for s in template['steps'] if s['required']
                ]
            }
            for key, template in self.WORKFLOW_TEMPLATES.items()
        }
    
    def start_workflow(
        self,
        user_id: str,
        workflow_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowState:
        """
        Start a new consent workflow.
        
        Args:
            user_id: User identifier
            workflow_type: Type of workflow (from templates)
            metadata: Optional additional metadata
            
        Returns:
            New WorkflowState object
        """
        template = self.WORKFLOW_TEMPLATES.get(workflow_type)
        if not template:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        # Check if user already has an active workflow of this type
        for workflow in self._workflows.values():
            if (workflow.user_id == user_id and 
                workflow.workflow_type == workflow_type and
                workflow.status == WorkflowStatus.IN_PROGRESS):
                return workflow
        
        # Create workflow steps
        steps = []
        for i, step_template in enumerate(template['steps']):
            step = WorkflowStep(
                step_id=str(uuid.uuid4()),
                step_number=i + 1,
                consent_type=step_template['consent_type'],
                title=step_template['title'],
                description=step_template['description'],
                required=step_template['required']
            )
            steps.append(step)
        
        now = datetime.now(timezone.utc).isoformat()
        
        workflow = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            user_id=user_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.IN_PROGRESS,
            current_step=1,
            total_steps=len(steps),
            steps=steps,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )
        
        self._workflows[workflow.workflow_id] = workflow
        self._save_workflows()
        
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def get_user_workflows(self, user_id: str) -> List[WorkflowState]:
        """Get all workflows for a user."""
        return [w for w in self._workflows.values() if w.user_id == user_id]
    
    def get_current_step(self, workflow_id: str) -> Optional[WorkflowStep]:
        """Get the current step in a workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.IN_PROGRESS:
            return None
        
        if workflow.current_step <= len(workflow.steps):
            return workflow.steps[workflow.current_step - 1]
        return None
    
    def get_step_consent_text(self, workflow_id: str, step_number: int) -> Dict[str, Any]:
        """Get the consent text for a specific step."""
        workflow = self.get_workflow(workflow_id)
        if not workflow or step_number > len(workflow.steps):
            return {}
        
        step = workflow.steps[step_number - 1]
        template = self.consent_manager.get_consent_template(step.consent_type)
        
        return {
            'step_number': step_number,
            'total_steps': workflow.total_steps,
            'title': step.title,
            'description': step.description,
            'consent_type': step.consent_type.value,
            'required': step.required,
            'consent_text': template.get('text', ''),
            'version': template.get('version', '1.0.0')
        }
    
    def process_step(
        self,
        workflow_id: str,
        step_number: int,
        accepted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a consent decision for a workflow step.
        
        Args:
            workflow_id: Workflow identifier
            step_number: Step number being processed
            accepted: Whether the consent was accepted
            ip_address: User's IP address
            user_agent: User's browser info
            
        Returns:
            Dictionary with result and next step info
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}
        
        if workflow.status != WorkflowStatus.IN_PROGRESS:
            return {'success': False, 'error': f'Workflow is {workflow.status.value}'}
        
        if step_number != workflow.current_step:
            return {'success': False, 'error': 'Invalid step number'}
        
        step = workflow.steps[step_number - 1]
        now = datetime.now(timezone.utc)
        
        # Create consent record
        consent = self.consent_manager.create_consent(
            user_id=workflow.user_id,
            consent_type=step.consent_type,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={
                'workflow_id': workflow_id,
                'step_number': step_number
            }
        )
        
        step.consent_id = consent.consent_id
        
        if accepted:
            # Grant the consent
            self.consent_manager.grant_consent(consent.consent_id)
            step.status = ConsentStatus.GRANTED
            step.completed_at = now.isoformat()
        else:
            # Deny the consent
            self.consent_manager.deny_consent(consent.consent_id)
            step.status = ConsentStatus.DENIED
            
            # If required step is denied, cancel workflow
            if step.required:
                workflow.status = WorkflowStatus.CANCELLED
                workflow.updated_at = now.isoformat()
                self._save_workflows()
                return {
                    'success': True,
                    'workflow_cancelled': True,
                    'reason': f'Required consent "{step.title}" was denied'
                }
        
        # Move to next step
        workflow.current_step += 1
        workflow.updated_at = now.isoformat()
        
        # Check if workflow is complete
        if workflow.current_step > workflow.total_steps:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = now.isoformat()
            self._save_workflows()
            return {
                'success': True,
                'workflow_completed': True,
                'summary': self.get_workflow_summary(workflow_id)
            }
        
        self._save_workflows()
        
        return {
            'success': True,
            'next_step': workflow.current_step,
            'next_step_info': self.get_step_consent_text(workflow_id, workflow.current_step)
        }
    
    def skip_optional_step(self, workflow_id: str, step_number: int) -> Dict[str, Any]:
        """
        Skip an optional consent step.
        
        Args:
            workflow_id: Workflow identifier
            step_number: Step number to skip
            
        Returns:
            Dictionary with result
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {'success': False, 'error': 'Workflow not found'}
        
        step = workflow.steps[step_number - 1]
        
        if step.required:
            return {'success': False, 'error': 'Cannot skip required step'}
        
        step.skipped = True
        step.status = ConsentStatus.DENIED
        step.completed_at = datetime.now(timezone.utc).isoformat()
        
        workflow.current_step += 1
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        
        if workflow.current_step > workflow.total_steps:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = workflow.updated_at
        
        self._save_workflows()
        
        return {
            'success': True,
            'skipped': True,
            'next_step': workflow.current_step if workflow.current_step <= workflow.total_steps else None
        }
    
    def cancel_workflow(self, workflow_id: str, reason: Optional[str] = None) -> bool:
        """Cancel an in-progress workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.IN_PROGRESS:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.updated_at = datetime.now(timezone.utc).isoformat()
        workflow.metadata['cancellation_reason'] = reason
        
        self._save_workflows()
        return True
    
    def get_workflow_summary(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get a summary of a workflow's status.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Dictionary with workflow summary
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {}
        
        granted = [s for s in workflow.steps if s.status == ConsentStatus.GRANTED]
        denied = [s for s in workflow.steps if s.status == ConsentStatus.DENIED and not s.skipped]
        skipped = [s for s in workflow.steps if s.skipped]
        pending = [s for s in workflow.steps if s.status == ConsentStatus.PENDING]
        
        return {
            'workflow_id': workflow_id,
            'workflow_type': workflow.workflow_type,
            'status': workflow.status.value,
            'progress': f"{len(granted) + len(denied) + len(skipped)}/{workflow.total_steps}",
            'granted_consents': [s.consent_type.value for s in granted],
            'denied_consents': [s.consent_type.value for s in denied],
            'skipped_consents': [s.consent_type.value for s in skipped],
            'pending_consents': [s.consent_type.value for s in pending],
            'created_at': workflow.created_at,
            'completed_at': workflow.completed_at,
            'all_required_granted': all(
                s.status == ConsentStatus.GRANTED 
                for s in workflow.steps if s.required
            )
        }
    
    def is_workflow_complete(self, workflow_id: str) -> bool:
        """Check if a workflow is complete."""
        workflow = self.get_workflow(workflow_id)
        return workflow is not None and workflow.status == WorkflowStatus.COMPLETED
    
    def has_required_consents(self, user_id: str, workflow_type: str) -> bool:
        """
        Check if a user has completed required consents for a workflow type.
        
        Args:
            user_id: User identifier
            workflow_type: Workflow type to check
            
        Returns:
            True if all required consents are granted
        """
        template = self.WORKFLOW_TEMPLATES.get(workflow_type)
        if not template:
            return False
        
        for step in template['steps']:
            if step['required']:
                if not self.consent_manager.check_consent(user_id, step['consent_type']):
                    return False
        
        return True
