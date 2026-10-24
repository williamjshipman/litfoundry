"""Data root initialization."""

import sys
from pathlib import Path

from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade
from litfoundry.config import Config
from litfoundry.constants import ProductConstants
from litfoundry.filesystem import apply_permissions
from litfoundry.secrets import SecretManager


def initialize_data_root(root: Path, recreate: bool = False) -> None:
    """Initialize a new LitFoundry data root.

    Args:
        root: Path to the data root
        recreate: If True, skip initialization if the root already exists

    Raises:
        ValueError: If the path is unsafe or on a network filesystem
        OSError: If initialization fails
    """
    # Validate the root path
    Config.validate_data_root(root)

    # Check if already initialized
    if root.exists():
        if not recreate:
            # Already initialized, idempotent
            return
        # Recreate: continue with initialization

    # Create directory structure
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    (root / "secret_material").mkdir(exist_ok=True)
    (root / "projects").mkdir(exist_ok=True)

    # Apply restrictive permissions to data root and subdirectories
    apply_permissions(root)

    # Create and initialize secrets (master key and session signing key)
    secret_manager = SecretManager(root / "secret_material")
    secret_manager.ensure_keys_exist()

    # Create catalogue database at latest revision
    catalog_path = root / "catalog.sqlite"
    if not catalog_path.exists():
        # Create engine with proper configuration
        engine = create_catalog_engine(catalog_path)

        # Run Alembic upgrade to baseline
        try:
            run_alembic_upgrade(catalog_path, target_revision="head")
        except Exception as e:
            raise OSError(f"Failed to initialize catalogue: {e}") from e

    # Mark initialization complete (touch a marker file)
    (root / ".initialized").touch()


def reinitialize_data_root(root: Path) -> None:
    """Re-initialize an existing data root (idempotent)."""
    initialize_data_root(root, recreate=False)
