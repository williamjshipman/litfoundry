"""Structured JSON logging for LitFoundry."""

import json
import logging
import re
from logging import Formatter, LogRecord
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class RedactionFilter(logging.Filter):
    """Filter that redacts sensitive information from log records."""

    # Patterns for common secret types
    REDACTION_PATTERNS = [
        # Passwords, secrets, tokens, keys
        (r'"password"\s*:\s*"[^"]*"', '"password": "***"'),
        (r'"secret"\s*:\s*"[^"]*"', '"secret": "***"'),
        (r'"token"\s*:\s*"[^"]*"', '"token": "***"'),
        (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "***"'),
        (r'"apikey"\s*:\s*"[^"]*"', '"apikey": "***"'),
        (r'"refresh_token"\s*:\s*"[^"]*"', '"refresh_token": "***"'),
        (r'"access_token"\s*:\s*"[^"]*"', '"access_token": "***"'),
        (r'"csrf_token"\s*:\s*"[^"]*"', '"csrf_token": "***"'),
        (r'"session_token"\s*:\s*"[^"]*"', '"session_token": "***"'),
        (r'"bootstrap_token"\s*:\s*"[^"]*"', '"bootstrap_token": "***"'),
        (r'"service_account_password"\s*:\s*"[^"]*"', '"service_account_password": "***"'),
        (r'"ldap_password"\s*:\s*"[^"]*"', '"ldap_password": "***"'),
        # OAuth/OIDC
        (r'"client_secret"\s*:\s*"[^"]*"', '"client_secret": "***"'),
        (r'"authorization"\s*:\s*"Bearer\s+[^\s"]*"', '"authorization": "Bearer ***"'),
        (r'"authorization"\s*:\s*"Basic\s+[^\s"]*"', '"authorization": "Basic ***"'),
        # Common field names with values
        (r'password\s*=\s*[^\s,;}\]]*', 'password=***'),
        (r'token\s*=\s*[^\s,;}\]]*', 'token=***'),
        (r'key\s*=\s*[^\s,;}\]]*', 'key=***'),
        (r'secret\s*=\s*[^\s,;}\]]*', 'secret=***'),
        # Catch quoted passwords in exception messages (e.g., 'password is "SECRET"')
        (r'(?i)password\s+is\s+"([^"]*)"', r'password is "***"'),
    ]

    def filter(self, record: LogRecord) -> bool:
        """Redact sensitive information from the log record.

        Applies redaction to:
        - Message and formatted arguments
        - Exception text and tracebacks
        """
        # Redact message
        msg = record.getMessage()
        for pattern, replacement in self.REDACTION_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        record.msg = msg
        record.args = ()

        # Redact exception text if present
        # exc_text is the formatted exception string (including traceback)
        if record.exc_text:
            for pattern, replacement in self.REDACTION_PATTERNS:
                record.exc_text = re.sub(
                    pattern, replacement, record.exc_text, flags=re.IGNORECASE
                )

        return True


class JSONFormatter(Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, process_name: str = "litfoundry"):
        """Initialize the JSON formatter.
        
        Args:
            process_name: Name of the process (e.g., 'litfoundry-server', 'litfoundry-worker')
        """
        super().__init__()
        self.process_name = process_name

    def format(self, record: LogRecord) -> str:
        """Format a log record as JSON.

        Ensures UTC timestamps and includes required event field.
        """
        # Format timestamp in UTC (Z suffix indicates UTC)
        import time

        ct = time.gmtime(record.created)  # Use gmtime for UTC, not localtime
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", ct)
        # Add milliseconds manually
        milliseconds = int((record.created % 1) * 1000)
        timestamp = f"{timestamp}.{milliseconds:03d}Z"

        log_obj: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "event": record.name,  # Required field for structured logging
            "process": self.process_name,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add optional fields if present
        if hasattr(record, "request_id") and record.request_id:
            log_obj["request_id"] = record.request_id

        if hasattr(record, "job_id") and record.job_id:
            log_obj["job_id"] = record.job_id
        
        if hasattr(record, "project_id") and record.project_id:
            log_obj["project_id"] = record.project_id
        
        if hasattr(record, "user_id") and record.user_id:
            log_obj["user_id"] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)


def setup_logging(
    data_root: Path,
    process_name: str = "litfoundry",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 10,  # 10 files
) -> None:
    """Set up structured JSON logging for LitFoundry.
    
    Args:
        data_root: Path to the data root directory
        process_name: Name of the process (server, worker, etc.)
        level: Logging level (default: INFO)
        max_bytes: Maximum size of a log file before rotation
        backup_count: Number of backup files to keep
    """
    logs_dir = data_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create rotating file handler
    log_file = logs_dir / "litfoundry.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(level)
    
    # Create formatter and filter
    formatter = JSONFormatter(process_name=process_name)
    redaction_filter = RedactionFilter()
    
    # Attach formatter and filter
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redaction_filter)
    
    # Add handler to root logger
    root_logger.addHandler(file_handler)


def get_structured_logger(name: str) -> logging.LoggerAdapter:
    """Get a structured logger with context support.
    
    Returns a LoggerAdapter that supports adding structured fields
    like request_id, job_id, etc.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        A LoggerAdapter for structured logging
    """
    base_logger = logging.getLogger(name)
    return logging.LoggerAdapter(base_logger, {})
