"""Tests for the CLI."""

import subprocess


class TestCLI:
    """CLI tests."""

    def test_version(self):
        """Test litfoundry --version."""
        result = subprocess.run(
            ["litfoundry", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "1.0.0" in result.stdout
        assert result.returncode == 0

    def test_help(self):
        """Test litfoundry --help."""
        result = subprocess.run(
            ["litfoundry", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "LitFoundry" in result.stdout
        assert "init" in result.stdout
        assert "serve" in result.stdout
