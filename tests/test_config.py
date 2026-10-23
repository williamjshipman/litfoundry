"""Tests for configuration."""

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from litfoundry.config import Config


class TestConfigDefaults:
    """Test configuration defaults."""

    def test_default_data_root_windows(self):
        """Test Windows data root default."""
        with mock.patch.object(sys, "platform", "win32"):
            with mock.patch.dict(os.environ, {"PROGRAMDATA": "C:\\ProgramData"}):
                root = Config.get_default_data_root()
                assert str(root) == "C:\\ProgramData\\LitFoundry"

    def test_default_data_root_macos(self):
        """Test macOS data root default."""
        with mock.patch.object(sys, "platform", "darwin"):
            root = Config.get_default_data_root()
            assert "Application Support" in str(root)
            assert "LitFoundry" in str(root)

    def test_default_data_root_linux(self):
        """Test Linux data root default."""
        with mock.patch.object(sys, "platform", "linux"):
            root = Config.get_default_data_root()
            # Check path parts, not string representation (Windows uses backslashes)
            assert root.name == "litfoundry"
            assert "lib" in root.parts

    def test_default_run_mode(self):
        """Test default run mode."""
        config = Config()
        assert config.LITFOUNDRY_RUN_MODE == "server"

    def test_default_port(self):
        """Test default port."""
        config = Config()
        assert config.LITFOUNDRY_PORT == 5080

    def test_default_allowed_hosts(self):
        """Test default allowed hosts."""
        config = Config()
        assert "localhost" in config.LITFOUNDRY_ALLOWED_HOSTS
        assert "127.0.0.1" in config.LITFOUNDRY_ALLOWED_HOSTS


class TestConfigLoading:
    """Test loading configuration from environment."""

    def test_load_from_env_overrides(self):
        """Test that environment variables override defaults."""
        with mock.patch.dict(
            os.environ,
            {
                "LITFOUNDRY_PORT": "8080",
                "LITFOUNDRY_RUN_MODE": "workstation",
                "LITFOUNDRY_ALLOWED_HOSTS": "custom.local",
            },
        ):
            config = Config.load_from_env()
            assert config.LITFOUNDRY_PORT == 8080
            assert config.LITFOUNDRY_RUN_MODE == "workstation"
            assert config.LITFOUNDRY_ALLOWED_HOSTS == "custom.local"

    def test_load_from_env_keeps_defaults(self):
        """Test that defaults are kept when env variables are not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = Config.load_from_env()
            assert config.LITFOUNDRY_PORT == 5080
            assert config.LITFOUNDRY_RUN_MODE == "server"

    def test_unprefixed_variables_ignored(self):
        """Test that non-LITFOUNDRY_ prefixed variables are ignored."""
        with mock.patch.dict(
            os.environ, {"PORT": "9000", "LITFOUNDRY_PORT": "8080"}
        ):
            config = Config.load_from_env()
            # Should load LITFOUNDRY_PORT, ignore PORT
            assert config.LITFOUNDRY_PORT == 8080

    def test_port_type_conversion(self):
        """Test that port is converted to int."""
        with mock.patch.dict(os.environ, {"LITFOUNDRY_PORT": "3000"}):
            config = Config.load_from_env()
            assert config.LITFOUNDRY_PORT == 3000
            assert isinstance(config.LITFOUNDRY_PORT, int)

    def test_invalid_port_keeps_default(self):
        """Test that invalid port value keeps default."""
        with mock.patch.dict(os.environ, {"LITFOUNDRY_PORT": "invalid"}):
            config = Config.load_from_env()
            assert config.LITFOUNDRY_PORT == 5080


class TestConfigToDict:
    """Test configuration export."""

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = Config()
        config_dict = config.to_dict()
        assert "LITFOUNDRY_PORT" in config_dict
        assert "LITFOUNDRY_RUN_MODE" in config_dict
        assert config_dict["LITFOUNDRY_PORT"] == 5080
