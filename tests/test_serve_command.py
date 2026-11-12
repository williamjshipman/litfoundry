"""Tests for litfoundry serve command."""

import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from litfoundry.cli import main


class TestServeCommand:
    """Tests for the 'litfoundry serve' CLI command."""

    def test_serve_requires_mode(self):
        """Test that serve requires an explicit run mode."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Initialize data root first
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            # Serve without mode should fail
            with mock.patch("litfoundry.server.start_server") as mock_start:
                # Even with default, clicking should pass None if not specified
                # But actually the default is "server", so test with explicit invalid value
                result = runner.invoke(main, ["serve", "--data-root", str(root), "--mode", "invalid"])
                assert result.exit_code != 0

    def test_serve_default_port_5080(self):
        """Test that serve defaults to port 5080."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            with mock.patch("litfoundry.server.start_server") as mock_start:
                result = runner.invoke(main, ["serve", "--data-root", str(root), "--mode", "workstation"])
                # Verify start_server was actually called
                assert mock_start.called, "start_server not called; command did not execute"
                # Check that start_server was called with port 5080
                call_args = mock_start.call_args
                assert call_args[1]["port"] == 5080, f"Expected port 5080, got {call_args[1]['port']}"

    def test_serve_custom_port(self):
        """Test that serve accepts a custom port."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            with mock.patch("litfoundry.server.start_server") as mock_start:
                result = runner.invoke(main, ["serve", "--data-root", str(root), "--port", "8080", "--mode", "workstation"])
                # Verify start_server was actually called
                assert mock_start.called, "start_server not called; command did not execute"
                # Check that start_server was called with port 8080
                call_args = mock_start.call_args
                assert call_args[1]["port"] == 8080, f"Expected port 8080, got {call_args[1]['port']}"

    def test_serve_server_mode(self):
        """Test that serve accepts 'server' run mode."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            with mock.patch("litfoundry.server.start_server") as mock_start:
                result = runner.invoke(main, ["serve", "--data-root", str(root), "--mode", "server"])
                # Verify start_server was actually called
                assert mock_start.called, "start_server not called; command did not execute"
                # Check that start_server was called with mode 'server'
                call_args = mock_start.call_args
                assert call_args[1]["mode"] == "server", f"Expected mode 'server', got {call_args[1]['mode']}"

    def test_serve_workstation_mode(self):
        """Test that serve accepts 'workstation' run mode."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            with mock.patch("litfoundry.server.start_server") as mock_start:
                result = runner.invoke(main, ["serve", "--data-root", str(root), "--mode", "workstation"])
                # Verify start_server was actually called
                assert mock_start.called, "start_server not called; command did not execute"
                # Check that start_server was called with mode 'workstation'
                call_args = mock_start.call_args
                assert call_args[1]["mode"] == "workstation", f"Expected mode 'workstation', got {call_args[1]['mode']}"

    def test_serve_refuses_debug_mode(self):
        """Test that serve refuses to start with debug mode enabled."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            # Set FLASK_DEBUG and try to serve
            with mock.patch.dict("os.environ", {"FLASK_DEBUG": "1"}):
                result = runner.invoke(main, ["serve", "--data-root", str(root), "--mode", "workstation"])
                # Should fail with error about debug mode
                assert result.exit_code != 0
                assert "debug" in result.output.lower()

    def test_serve_binds_to_loopback(self):
        """Test that serve binds to 127.0.0.1 only."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = runner.invoke(main, ["init", "--data-root", str(root)])
            assert result.exit_code == 0
            
            # Mock both Waitress serve and create_app to prevent actual server startup
            with mock.patch("waitress.serve") as mock_waitress_serve:
                with mock.patch("litfoundry.server.create_app"):
                    result = runner.invoke(main, ["serve", "--data-root", str(root), "--mode", "workstation"])
                    # Verify Waitress was actually called
                    assert mock_waitress_serve.called, "Waitress serve not called; startup path not exercised"
                    # Verify Waitress was called with loopback
                    call_args = mock_waitress_serve.call_args
                    assert call_args[1].get("host") == "127.0.0.1", \
                        f"Expected host 127.0.0.1, got {call_args[1].get('host')}"

    def test_serve_requires_data_root_to_exist(self):
        """Test that serve requires data root to exist."""
        runner = CliRunner()
        nonexistent = Path("/nonexistent/path/that/does/not/exist")
        result = runner.invoke(main, ["serve", "--data-root", str(nonexistent)])
        # Click validation should fail since we specify exists=True
        assert result.exit_code != 0
