"""Catalogue database management."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

# Track if pragmas event handler is already registered
_pragmas_registered = False


def create_catalog_engine(catalog_path: Path) -> Engine:
    """Create a catalogue database engine with proper configuration.

    Args:
        catalog_path: Path to the catalog.sqlite database file

    Returns:
        SQLAlchemy engine configured for LitFoundry
    """
    global _pragmas_registered
    
    # Create the engine with SQLite
    engine = create_engine(
        f"sqlite:///{catalog_path}",
        echo=False,
        poolclass=None,  # Don't pool for SQLite
    )

    # Configure SQLite pragmas on each connection (register only once)
    if not _pragmas_registered:
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragmas(dbapi_conn, connection_record):
            """Set SQLite pragmas for production use."""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
            cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
            cursor.execute("PRAGMA busy_timeout=5000")  # 5-second busy timeout
            cursor.close()
        
        _pragmas_registered = True

    return engine


def run_alembic_upgrade(catalog_path: Path, target_revision: str = "head") -> None:
    """Run Alembic migrations for the catalogue database.

    Args:
        catalog_path: Path to the catalog.sqlite database file
        target_revision: Target revision (default: 'head')
    """
    from alembic import command
    from alembic.config import Config

    # Get the migrations directory (relative to project root)
    # This file is at: src/litfoundry/catalog/engine.py
    # Migrations are at: migrations/catalog/
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent  # Go up to project root
    migrations_dir = project_root / "migrations" / "catalog"

    # Create Alembic config
    alembic_cfg = Config(str(migrations_dir / "alembic.ini"))
    alembic_cfg.set_main_option(
        "sqlalchemy.url", f"sqlite:///{catalog_path}"
    )
    alembic_cfg.set_main_option("script_location", str(migrations_dir))

    # Run upgrade
    command.upgrade(alembic_cfg, target_revision)