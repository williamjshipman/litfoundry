"""Tests for structured JSON logging and redaction."""

import json
import logging
import tempfile
from pathlib import Path

import pytest

from litfoundry.logging import (
    JSONFormatter,
    RedactionFilter,
    get_structured_logger,
    setup_logging,
)


class TestRedactionFilter:
    """Tests for the redaction filter."""

    def test_redaction_filter_redacts_password(self):
        """Redaction filter should redact password fields."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"password": "mysecretpass"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "mysecretpass" not in record.getMessage()
        assert "***" in record.getMessage()

    def test_redaction_filter_redacts_token(self):
        """Redaction filter should redact token fields."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"token": "abc123xyz"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "abc123xyz" not in record.getMessage()
        assert "***" in record.getMessage()

    def test_redaction_filter_redacts_api_key(self):
        """Redaction filter should redact API key fields."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"api_key": "sk-12345"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "sk-12345" not in record.getMessage()
        assert "***" in record.getMessage()

    def test_redaction_filter_redacts_refresh_token(self):
        """Redaction filter should redact refresh token fields."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"refresh_token": "refresh123"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "refresh123" not in record.getMessage()
        assert "***" in record.getMessage()

    def test_redaction_filter_redacts_csrf_token(self):
        """Redaction filter should redact CSRF tokens."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"csrf_token": "csrf_value_123"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "csrf_value_123" not in record.getMessage()
        assert "***" in record.getMessage()

    def test_redaction_filter_redacts_authorization_header(self):
        """Redaction filter should redact Authorization headers."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"authorization": "Bearer eyJhbGciOiJIUzI1NiJ9"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "eyJhbGciOiJIUzI1NiJ9" not in record.getMessage()
        assert "Bearer ***" in record.getMessage()

    def test_redaction_filter_redacts_multiple_secrets(self):
        """Redaction filter should redact multiple secrets in one message."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"password": "pass123", "api_key": "key456"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        msg = record.getMessage()
        
        assert "pass123" not in msg
        assert "key456" not in msg
        assert msg.count("***") >= 2

    def test_redaction_filter_preserves_non_secret_data(self):
        """Redaction filter should not modify non-secret fields."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"user_id": "12345", "message": "Login successful"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "12345" in record.getMessage()
        assert "Login successful" in record.getMessage()

    def test_redaction_filter_case_insensitive(self):
        """Redaction filter should work case-insensitively."""
        filt = RedactionFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='{"PASSWORD": "secretpass"}',
            args=(),
            exc_info=None,
        )
        
        filt.filter(record)
        
        assert "secretpass" not in record.getMessage()


class TestJSONFormatter:
    """Tests for the JSON formatter."""

    def test_json_formatter_creates_valid_json(self):
        """JSON formatter should create valid JSON."""
        formatter = JSONFormatter(process_name="test-process")
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        
        # Should parse as valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_formatter_includes_required_fields(self):
        """JSON formatter should include all required fields."""
        formatter = JSONFormatter(process_name="test-process")
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "process" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["process"] == "test-process"

    def test_json_formatter_includes_request_id_when_present(self):
        """JSON formatter should include request_id if present."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Request failed",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["request_id"] == "req-123"

    def test_json_formatter_includes_job_id_when_present(self):
        """JSON formatter should include job_id if present."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Job started",
            args=(),
            exc_info=None,
        )
        record.job_id = "job-456"
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert parsed["job_id"] == "job-456"

    def test_json_formatter_includes_exception_info(self):
        """JSON formatter should include exception info when present."""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="An error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "Test error" in parsed["exception"]

    def test_json_formatter_omits_unset_optional_fields(self):
        """JSON formatter should not include unset optional fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Simple message",
            args=(),
            exc_info=None,
        )
        
        result = formatter.format(record)
        parsed = json.loads(result)
        
        assert "request_id" not in parsed
        assert "job_id" not in parsed
        assert "exception" not in parsed


class TestLoggingSetup:
    """Tests for logging setup."""

    @pytest.fixture(autouse=True)
    def cleanup_logging(self):
        """Clean up logging handlers after each test."""
        yield
        # Remove all handlers to release file handles on Windows
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()

    def test_setup_logging_creates_logs_directory(self, tmp_path):
        """setup_logging should create logs directory if it doesn't exist."""
        logs_dir = tmp_path / "logs"
        
        assert not logs_dir.exists()
        
        setup_logging(tmp_path)
        
        assert logs_dir.exists()
        assert logs_dir.is_dir()

    def test_setup_logging_creates_log_file(self, tmp_path):
        """setup_logging should create a log file."""
        setup_logging(tmp_path)
        
        log_file = tmp_path / "logs" / "litfoundry.log"
        assert log_file.exists()

    def test_setup_logging_writes_json_logs(self, tmp_path):
        """setup_logging should write JSON-formatted logs."""
        setup_logging(tmp_path, level=logging.INFO)
        
        logger = logging.getLogger("test.module")
        logger.info("Test log message")
        
        log_file = tmp_path / "logs" / "litfoundry.log"
        content = log_file.read_text()
        
        # Should be valid JSON
        parsed = json.loads(content)
        assert parsed["message"] == "Test log message"
        assert parsed["level"] == "INFO"

    def test_setup_logging_redacts_secrets_in_output(self, tmp_path):
        """setup_logging should redact secrets from log output."""
        setup_logging(tmp_path, level=logging.INFO)
        
        logger = logging.getLogger("test")
        logger.info('{"password": "mysecret123"}')
        
        log_file = tmp_path / "logs" / "litfoundry.log"
        content = log_file.read_text()
        
        assert "mysecret123" not in content
        assert "***" in content

    def test_setup_logging_rotation(self, tmp_path):
        """setup_logging should rotate logs when size limit is reached."""
        # Set small file size to force rotation
        setup_logging(tmp_path, max_bytes=100, backup_count=2)
        
        logger = logging.getLogger("test")
        
        # Write multiple messages to trigger rotation
        for i in range(10):
            logger.info(f"Message {i}: " + "x" * 50)
        
        logs_dir = tmp_path / "logs"
        log_files = list(logs_dir.glob("litfoundry.log*"))
        
        # Should have at least the main log and some backups
        assert len(log_files) >= 2

    def test_setup_logging_respects_process_name(self, tmp_path):
        """setup_logging should use the provided process name."""
        setup_logging(tmp_path, process_name="litfoundry-worker")
        
        logger = logging.getLogger("test")
        logger.info("Test message")
        
        log_file = tmp_path / "logs" / "litfoundry.log"
        content = log_file.read_text()
        
        parsed = json.loads(content)
        assert parsed["process"] == "litfoundry-worker"




class TestStructuredLogger:
    """Tests for the structured logger adapter."""

    @pytest.fixture(autouse=True)
    def cleanup_logging(self):
        """Clean up logging handlers after each test."""
        yield
        # Remove all handlers to release file handles on Windows
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()

    def test_get_structured_logger_returns_adapter(self):
        """get_structured_logger should return a LoggerAdapter."""
        logger = get_structured_logger("test")
        
        assert isinstance(logger, logging.LoggerAdapter)

    def test_structured_logger_can_log(self, tmp_path):
        """Structured logger should be able to log messages."""
        setup_logging(tmp_path)
        
        logger = get_structured_logger("test.module")
        
        # Should not raise
        logger.info("Test message")
        logger.warning("Warning message")
        logger.error("Error message")

