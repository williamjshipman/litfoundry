"""Type definitions for background jobs."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Dict, List
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    RUNNING = "running"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class WriteScope(str, Enum):
    """Write scope for a job."""
    APPEND = "append"
    RECORDS = "records"
    PROJECT = "project"


@dataclass
class JobProgress:
    """Structured progress data for a job."""
    message: str = ""
    percent_complete: Optional[float] = None
    current_item: Optional[str] = None
    total_items: Optional[int] = None
    failed_items: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class JobResult:
    """Result of a job execution."""
    status: JobStatus
    progress: Optional[JobProgress] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_cause: Optional[str] = None
    output: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "progress": self.progress.to_dict() if self.progress else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_cause": self.error_cause,
            "output": self.output,
        }


class RetryableError(Exception):
    """Exception indicating the job should be retried."""
    
    def __init__(self, message: str, error_code: str = "RETRYABLE_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class NonRetryableError(Exception):
    """Exception indicating the job should not be retried."""
    
    def __init__(self, message: str, error_code: str = "JOB_FAILED", error_cause: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.error_cause = error_cause


@dataclass
class Job:
    """A background job."""
    id: str
    project_id: Optional[str]
    user_id: str
    type: str
    status: JobStatus
    scope_json: Optional[str] = None
    priority: int = 50
    not_before: datetime = field(default_factory=datetime.utcnow)
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    attempt: int = 1
    max_attempts: int = 3
    progress_json: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_cause: Optional[str] = None
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
