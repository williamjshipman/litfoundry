"""Tests for the status command and checking."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from litfoundry.cli import main
from litfoundry.initialization import initialize_data_root
from litfoundry.status import check_status


class TestStatusCommand:
    """Tests for the `litfoundry status` CLI command."""

    def test_status_with_healthy_data_root(self, tmp_path):
        """Status command should exit 0 for a healthy installation."""
        # Initialize a data root
        initialize_data_root(tmp_path)
        
        # Run status command
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--data-root", str(tmp_path)])
        
        assert result.exit_code == 0
        assert "HEALTHY" in result.output
        assert "Version:" in result.output
        assert "Health Checks:" in result.output

    def test_status_with_uninitialized_data_root(self, tmp_path):
        """Status command should exit non-zero for uninitialized root."""
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--data-root", str(tmp_path)])
        
        assert result.exit_code != 0
        assert "BROKEN" in result.output

    def test_status_output_contains_checks(self, tmp_path):
        """Status output should list all checks."""
        initialize_data_root(tmp_path)
        
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--data-root", str(tmp_path)])
        
        # Should list individual checks
        assert "data_root:" in result.output or "data_root :" in result.output.lower()
        assert "catalogue:" in result.output or "catalogue :" in result.output.lower()
        assert "initialization:" in result.output or "initialization :" in result.output.lower()

    def test_status_with_missing_data_root(self):
        """Status command should handle missing data root gracefully."""
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--data-root", "/nonexistent/path"])
        
        assert result.exit_code != 0


class TestStatusChecking:
    """Tests for the status checking function."""

    def test_check_status_healthy_returns_dict(self, tmp_path):
        """check_status should return a dict with expected keys."""
        initialize_data_root(tmp_path)
        
        result = check_status(tmp_path)
        
        assert isinstance(result, dict)
        assert "status" in result
        assert "healthy" in result
        assert "version" in result
        assert "checks" in result

    def test_check_status_healthy_data_root(self, tmp_path):
        """check_status should report healthy for initialized root."""
        initialize_data_root(tmp_path)
        
        result = check_status(tmp_path)
        
        assert result["status"] == "healthy"
        assert result["healthy"] is True
        assert result["version"]  # Should have a version

    def test_check_status_checks_data_root(self, tmp_path):
        """check_status should verify data root exists."""
        result = check_status(tmp_path)
        
        assert "data_root" in result["checks"]
        data_root_check = result["checks"]["data_root"]
        assert data_root_check["status"] in ("ok", "failed")

    def test_check_status_checks_initialization(self, tmp_path):
        """check_status should verify initialization marker."""
        initialize_data_root(tmp_path)
        
        result = check_status(tmp_path)
        
        assert "initialization" in result["checks"]
        init_check = result["checks"]["initialization"]
        assert init_check["status"] == "ok"

    def test_check_status_checks_catalogue(self, tmp_path):
        """check_status should verify catalogue database."""
        initialize_data_root(tmp_path)
        
        result = check_status(tmp_path)
        
        assert "catalogue" in result["checks"]
        catalogue_check = result["checks"]["catalogue"]
        assert catalogue_check["status"] == "ok"

    def test_check_status_checks_disk_space(self, tmp_path):
        """check_status should check available disk space."""
        initialize_data_root(tmp_path)
        
        result = check_status(tmp_path)
        
        assert "disk_space" in result["checks"]
        disk_check = result["checks"]["disk_space"]
        assert disk_check["status"] in ("ok", "warning", "failed")

    def test_check_status_uninitialized_root_fails(self, tmp_path):
        """check_status should fail for uninitialized root."""
        result = check_status(tmp_path)
        
        assert result["status"] == "broken"
        assert result["healthy"] is False
        assert result["checks"]["initialization"]["status"] == "failed"

    def test_check_status_missing_catalogue_fails(self, tmp_path):
        """check_status should fail if catalogue is missing."""
        # Create initialization marker but not catalogue
        initialized_marker = tmp_path / ".initialized"
        initialized_marker.touch()
        
        result = check_status(tmp_path)
        
        assert result["healthy"] is False
        assert result["checks"]["catalogue"]["status"] == "failed"

    def test_check_status_missing_root_fails(self):
        """check_status should fail if data root doesn't exist."""
        nonexistent = Path("/this/path/does/not/exist/x" + str(id(object())))
        
        result = check_status(nonexistent)
        
        assert result["healthy"] is False
        assert result["checks"]["data_root"]["status"] == "failed"

    def test_status_command_uses_default_data_root(self):
        """Status command without --data-root should use default."""
        runner = CliRunner()
        # Should not crash when using default data root
        result = runner.invoke(main, ["status"])
        # Depending on whether default root is initialized, may exit 0 or 1
        # but should not error
        assert "Status:" in result.output or "Error:" in result.output
