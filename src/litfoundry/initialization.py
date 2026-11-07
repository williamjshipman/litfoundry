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

    # Check if already initialized (look for marker file)
    initialized_marker = root / ".initialized"
    if initialized_marker.exists():
        if not recreate:
            # Already initialized, idempotent
            return
        # Recreate: continue with initialization

    # Create directory structure
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    (root / "secret_material").mkdir(exist_ok=True)
    (root / "projects").mkdir(exist_ok=True)
    (root / "trash").mkdir(exist_ok=True)
    (root / "backup_staging").mkdir(exist_ok=True)

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
    
    # Generate initial bootstrap token and write to file
    try:
        from litfoundry.auth.bootstrap import (
            generate_bootstrap_token,
            hash_bootstrap_token,
            write_bootstrap_token_file,
            get_bootstrap_token_expiry_time,
        )
        from litfoundry.catalog import BootstrapToken
        from sqlalchemy.orm import sessionmaker
        from datetime import datetime, timezone
        
        # Generate token
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        now = datetime.now(timezone.utc)
        expires_at = get_bootstrap_token_expiry_time(now)
        
        # Store in database
        Session = sessionmaker(bind=engine)
        session = Session()
        boot_token = BootstrapToken(
            token_hash=token_hash,
            expires_at=expires_at,
            consumed_at=None,
        )
        session.add(boot_token)
        session.commit()
        session.close()
        
        # Write to file
        write_bootstrap_token_file(root, token)
        
        # Print token to console during init
        print(f"\n{'='*60}")
        print(f"Bootstrap Token (valid for 30 minutes):")
        print(f"{token}")
        print(f"{'='*60}\n")
        print(f"Token saved to: {root / 'bootstrap-token.txt'}")
        print("Use this token to complete setup at: /setup")
        
    except Exception as e:
        # Don't fail initialization if token generation fails
        print(f"Warning: Could not generate bootstrap token: {e}", file=sys.stderr)

    # Mark initialization complete (touch a marker file)
    (root / ".initialized").touch()



def reinitialize_data_root(root: Path) -> None:
    """Re-initialize an existing data root (idempotent)."""
    initialize_data_root(root, recreate=False)
