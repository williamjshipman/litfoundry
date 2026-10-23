"""Configuration loader for LitFoundry."""

import os
import sys
from pathlib import Path
from typing import ClassVar


class Config:
    """LitFoundry configuration with platform defaults."""

    LITFOUNDRY_DATA_ROOT: str | None = None
    LITFOUNDRY_RUN_MODE: str = "server"  # server | workstation
    LITFOUNDRY_PORT: int = 5080
    LITFOUNDRY_TRUSTED_PROXIES: str = ""
    LITFOUNDRY_ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    LITFOUNDRY_CORS_ORIGINS: str = ""
    LITFOUNDRY_CATALOG_PATH: str | None = None

    # Process names
    LITFOUNDRY_SERVER_PROCESS_NAME: ClassVar[str] = "litfoundry-server"
    LITFOUNDRY_WORKER_PROCESS_NAME: ClassVar[str] = "litfoundry-worker"

    @classmethod
    def load_from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()

        # Load LITFOUNDRY_* prefixed variables
        for key in dir(config):
            if key.startswith("LITFOUNDRY_") and not key.endswith(("_PROCESS_NAME",)):
                env_value = os.getenv(key)
                if env_value is not None:
                    # Type conversion for known types
                    if key == "LITFOUNDRY_PORT":
                        try:
                            setattr(config, key, int(env_value))
                        except ValueError:
                            pass  # Keep default if conversion fails
                    else:
                        setattr(config, key, env_value)

        return config

    @staticmethod
    def get_default_data_root() -> Path:
        """Get the default data root for the current platform."""
        if sys.platform == "win32":
            # Windows: %PROGRAMDATA%\LitFoundry
            programdata = os.getenv("PROGRAMDATA")
            if not programdata:
                programdata = "C:\\ProgramData"
            return Path(programdata) / "LitFoundry"
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/LitFoundry
            return Path.home() / "Library" / "Application Support" / "LitFoundry"
        else:
            # Linux and others: /var/lib/litfoundry
            return Path("/var/lib/litfoundry")

    @staticmethod
    def validate_data_root(root: Path) -> None:
        """Validate that the data root is safe to use."""
        from litfoundry.filesystem import check_network_filesystem, check_path_safety

        check_path_safety(root)
        check_network_filesystem(root)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        result = {}
        for key in dir(self):
            if key.startswith("LITFOUNDRY_") and not key.endswith(("_PROCESS_NAME",)):
                result[key] = getattr(self, key)
        return result
