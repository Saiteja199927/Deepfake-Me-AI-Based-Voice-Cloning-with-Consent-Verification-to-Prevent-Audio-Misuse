"""
Consent Logger Module
Comprehensive logging for all consent-related interactions
"""

import json
import gzip
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import threading
import uuid


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(Enum):
    CONSENT_CREATED = "consent_created"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_DENIED = "consent_denied"
    CONSENT_REVOKED = "consent_revoked"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    ERROR = "error"


@dataclass
class LogEntry:
    log_id: str
    timestamp: str
    level: LogLevel
    category: LogCategory
    message: str
    user_id: Optional[str] = None
    consent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'log_id': self.log_id, 'timestamp': self.timestamp,
            'level': self.level.value, 'category': self.category.value,
            'message': self.message, 'user_id': self.user_id,
            'consent_id': self.consent_id, 'workflow_id': self.workflow_id,
            'ip_address': self.ip_address, 'metadata': self.metadata or {}
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ConsentLogger:
    MAX_LOG_SIZE = 10 * 1024 * 1024
    MAX_LOG_FILES = 10
    
    def __init__(self, log_dir: Optional[str] = None, enable_console: bool = True,
                 enable_file: bool = True, min_level: LogLevel = LogLevel.INFO):
        self.log_dir = Path(log_dir) if log_dir else Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.min_level = min_level
        self.current_log_file = self.log_dir / "consent_log.jsonl"
        self._lock = threading.Lock()
        self._log_buffer: List[LogEntry] = []
        self._buffer_max_size = 1000
        self.session_id = str(uuid.uuid4())
    
    def log(self, level: LogLevel, category: LogCategory, message: str,
            user_id: Optional[str] = None, consent_id: Optional[str] = None,
            workflow_id: Optional[str] = None, ip_address: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None) -> LogEntry:
        
        entry = LogEntry(
            log_id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc).isoformat(),
            level=level, category=category, message=message, user_id=user_id,
            consent_id=consent_id, workflow_id=workflow_id, ip_address=ip_address,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._log_buffer.append(entry)
            if len(self._log_buffer) > self._buffer_max_size:
                self._log_buffer.pop(0)
        
        if self.enable_console:
            ts = entry.timestamp[:19].replace('T', ' ')
            print(f"[{ts}] [{entry.level.value.upper():8}] [{entry.category.value}] {entry.message}")
        
        if self.enable_file:
            self._write_to_file(entry)
        
        return entry
    
    def _write_to_file(self, entry: LogEntry) -> None:
        with self._lock:
            try:
                with open(self.current_log_file, 'a', encoding='utf-8') as f:
                    f.write(entry.to_json() + '\n')
            except Exception as e:
                print(f"Error writing log: {e}")
    
    def log_consent_granted(self, consent_id: str, user_id: str, consent_type: str, ip: str = None):
        return self.log(LogLevel.INFO, LogCategory.CONSENT_GRANTED,
                       f"Consent granted: {consent_type}", user_id, consent_id, ip_address=ip)
    
    def log_consent_denied(self, consent_id: str, user_id: str, consent_type: str, ip: str = None):
        return self.log(LogLevel.WARNING, LogCategory.CONSENT_DENIED,
                       f"Consent denied: {consent_type}", user_id, consent_id, ip_address=ip)
    
    def log_workflow_started(self, workflow_id: str, user_id: str, workflow_type: str):
        return self.log(LogLevel.INFO, LogCategory.WORKFLOW_STARTED,
                       f"Workflow started: {workflow_type}", user_id, workflow_id=workflow_id)
    
    def log_workflow_completed(self, workflow_id: str, user_id: str, workflow_type: str):
        return self.log(LogLevel.INFO, LogCategory.WORKFLOW_COMPLETED,
                       f"Workflow completed: {workflow_type}", user_id, workflow_id=workflow_id)
    
    def get_recent_logs(self, count: int = 100) -> List[LogEntry]:
        return list(self._log_buffer[-count:])
    
    def get_statistics(self) -> Dict[str, Any]:
        return {'session_id': self.session_id, 'total_logs': len(self._log_buffer)}
