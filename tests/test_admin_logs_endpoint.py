"""Tests for the admin logs endpoint."""

import json
import logging
from pathlib import Path

import pytest

from litfoundry.app import create_app
from litfoundry.initialization import initialize_data_root


class TestAdminLogsEndpoint:
    """Tests for GET /api/v1/admin/logs endpoint."""

    def test_logs_endpoint_exists(self, tmp_path):
        """Logs endpoint should exist and be accessible."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        
        assert response.status_code in (200, 401, 403)

    def test_logs_endpoint_returns_json(self, tmp_path):
        """Logs endpoint should return valid JSON."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        
        assert response.content_type == "application/json"
        data = response.get_json()
        assert isinstance(data, dict)

    def test_logs_endpoint_returns_logs_array(self, tmp_path):
        """Logs endpoint should return an array of log entries."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        data = response.get_json()
        
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_logs_endpoint_returns_metadata(self, tmp_path):
        """Logs endpoint should return total and filtered counts."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        data = response.get_json()
        
        assert "total" in data
        assert "filtered" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["filtered"], int)

    def test_logs_endpoint_with_missing_log_file(self, tmp_path):
        """Logs endpoint should handle missing log file gracefully."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        data = response.get_json()
        
        # Should return successful response with empty logs
        assert response.status_code == 200
        assert data["logs"] == []
        assert data["total"] == 0

    def test_logs_endpoint_without_data_root(self):
        """Logs endpoint should handle missing data root gracefully."""
        app = create_app(config={})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        data = response.get_json()
        
        # Should return error response
        assert response.status_code in (503, 404, 200)
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_logs_endpoint_limit_parameter_validation(self, tmp_path):
        """Logs endpoint should validate and cap limit parameter."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Test with very large limit
        response = client.get("/api/v1/admin/logs?limit=5000")
        data = response.get_json()
        
        # Should be capped at 1000
        assert data["limit"] <= 1000

    def test_logs_endpoint_invalid_limit_defaults(self, tmp_path):
        """Logs endpoint should default to 100 if limit is invalid."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs?limit=invalid")
        data = response.get_json()
        
        # Should default to 100
        assert data["limit"] == 100

    def test_logs_endpoint_filters_level_parameter(self, tmp_path):
        """Logs endpoint should accept level filter parameter."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should not error with level filter
        response = client.get("/api/v1/admin/logs?level=ERROR")
        
        assert response.status_code == 200

    def test_logs_endpoint_filters_request_id_parameter(self, tmp_path):
        """Logs endpoint should accept request_id filter parameter."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should not error with request_id filter
        response = client.get("/api/v1/admin/logs?request_id=req-123")
        data = response.get_json()
        
        assert response.status_code == 200
        assert data["filtered"] == 0  # No logs with this request_id

    def test_logs_endpoint_filters_job_id_parameter(self, tmp_path):
        """Logs endpoint should accept job_id filter parameter."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should not error with job_id filter
        response = client.get("/api/v1/admin/logs?job_id=job-456")
        data = response.get_json()
        
        assert response.status_code == 200
        assert data["filtered"] == 0  # No logs with this job_id

    def test_logs_endpoint_filters_process_parameter(self, tmp_path):
        """Logs endpoint should accept process filter parameter."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should not error with process filter
        response = client.get("/api/v1/admin/logs?process=litfoundry-server")
        
        assert response.status_code == 200

    def test_logs_endpoint_combined_filters(self, tmp_path):
        """Logs endpoint should support combined filter parameters."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should not error with multiple filters
        response = client.get("/api/v1/admin/logs?level=ERROR&process=server&limit=10")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 10

    def test_logs_endpoint_symlink_escape_prevented(self, tmp_path):
        """Logs endpoint should reject symlinks that escape the data root."""
        initialize_data_root(tmp_path)
        
        # Create a file outside the data root
        outside_file = tmp_path.parent / "outside_litfoundry.log"
        outside_file.write_text("SECRET DATA OUTSIDE ROOT")
        
        # Create a symlink inside the data root pointing outside
        logs_dir = tmp_path / "logs"
        symlink_path = logs_dir / "litfoundry.log"
        if symlink_path.exists():
            symlink_path.unlink()
        
        # Try to create a symlink (may fail on Windows without admin)
        try:
            symlink_path.symlink_to(outside_file)
        except (OSError, NotImplementedError):
            # Symlinks not supported on this system, skip test
            pytest.skip("Symlinks not supported on this system")
        
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        
        # Should reject the symlink escape attempt with 400 error
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "escape" in data["error"].lower() or "validation" in data["error"].lower()
        
        # Verify the outside file content is NOT returned
        response_json = response.get_json()
        assert "SECRET DATA OUTSIDE ROOT" not in str(response_json)

    def test_logs_endpoint_malformed_log_file_handling(self, tmp_path):
        """Logs endpoint should handle malformed log entries gracefully."""
        initialize_data_root(tmp_path)
        
        # Create a malformed log file (overwrite if exists)
        logs_dir = tmp_path / "logs"
        log_file = logs_dir / "litfoundry.log"
        log_file.write_text("not valid json\n{\"valid\": \"json\"}\nmore invalid")
        
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        response = client.get("/api/v1/admin/logs")
        data = response.get_json()
        
        # Should handle gracefully and return the valid entry
        assert response.status_code == 200
        # The endpoint should skip malformed lines and parse valid ones
        assert data["total"] >= 1
