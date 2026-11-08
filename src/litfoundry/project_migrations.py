"""Project database migration and upgrade management."""

import os
import sqlite3
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from litfoundry.catalog import Base as CatalogBase
from litfoundry.catalog.engine import create_catalog_engine


def create_project_engine(project_path: Path) -> Engine:
    """Create a project database engine with proper configuration.
    
    Args:
        project_path: Path to the project directory (contains project.sqlite)
        
    Returns:
        SQLAlchemy engine configured for project databases
    """
    project_path = Path(project_path)
    project_db = project_path / "project.sqlite"
    
    # Ensure parent directory exists
    project_db.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert path to absolute and use forward slashes for SQLite URL
    abs_path = project_db.resolve()
    posix_path = abs_path.as_posix()
    db_url = f"sqlite:///{posix_path}"
    
    # Create the engine with SQLite, NullPool for no connection pooling
    engine = create_engine(
        db_url,
        echo=False,
        poolclass=None,  # NullPool - no connection pooling
    )

    # Configure SQLite pragmas on each connection (per task spec)
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragmas(dbapi_conn, connection_record):
        """Set SQLite pragmas for production use."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
        cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
        cursor.execute("PRAGMA busy_timeout=5000")  # 5-second busy timeout
        cursor.close()

    return engine


def run_alembic_upgrade_project(project_path: Path, target_revision: str = "head") -> None:
    """Run Alembic migrations for a project database.
    
    Args:
        project_path: Path to the project directory
        target_revision: Target revision (default: 'head')
    """
    project_path = Path(project_path)
    project_db = project_path / "project.sqlite"
    
    # Ensure database exists
    project_db.parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine and connection
    engine = create_project_engine(project_path)
    
    # Bootstrap: Create alembic_version table if needed
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                PRIMARY KEY (version_num)
            )
        """))
        conn.commit()
    
    # Run Alembic upgrade with the project connection
    # project_root should be the repository root
    project_root = Path(__file__).parent.parent.parent  # Up from src/litfoundry/
    migrations_dir = project_root / "migrations" / "project"
    
    if not migrations_dir.exists():
        raise RuntimeError(f"Project migrations directory not found: {migrations_dir}")
    
    alembic_cfg = Config(str(migrations_dir / "alembic.ini"))
    
    # Set the database URL
    abs_path = project_db.resolve()
    db_url = f"sqlite:///{abs_path.as_posix()}"
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    
    # Use the connection from engine to run migrations
    with engine.connect() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, target_revision)
        connection.commit()


def create_project_database(project_path: Path) -> None:
    """Create a new project database at the latest schema version.
    
    Args:
        project_path: Path to the project directory
    """
    project_path = Path(project_path)
    project_db = project_path / "project.sqlite"
    
    # Ensure parent directory exists
    project_db.parent.mkdir(parents=True, exist_ok=True)
    
    # Run migrations to bring database to current version
    run_alembic_upgrade_project(project_path, "head")


def get_project_schema_version(project_path: Path) -> int:
    """Get the current schema version of a project database.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        The schema version number (1-based)
    """
    project_path = Path(project_path)
    project_db = project_path / "project.sqlite"
    
    if not project_db.exists():
        return 0
    
    try:
        conn = sqlite3.connect(str(project_db))
        cursor = conn.cursor()
        
        # Get the latest version from alembic_version table
        cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return 0
        
        # Extract version number from revision ID (e.g., "001_initial" -> 1)
        version_str = row[0].split("_")[0]
        return int(version_str)
    except Exception:
        return 0


def get_latest_project_schema_version() -> int:
    """Get the latest project schema version defined in migrations.
    
    Returns:
        The latest schema version number
    """
    project_root = Path(__file__).parent.parent.parent  # Up from src/litfoundry/
    versions_dir = project_root / "migrations" / "project" / "versions"
    
    if not versions_dir.exists():
        return 0
    
    # Find the highest numbered migration file
    max_version = 0
    for f in versions_dir.glob("*.py"):
        if f.name == "__init__.py" or f.name == "__pycache__":
            continue
        # Extract version number from filename (e.g., "001_initial.py" -> 1)
        try:
            version = int(f.name.split("_")[0])
            max_version = max(max_version, version)
        except (ValueError, IndexError):
            pass
    
    return max_version


def backup_database(db_path: Path, backup_dir: Path, backup_name: str = None) -> Path:
    """Create a backup copy of a database file.
    
    Args:
        db_path: Path to the database to back up
        backup_dir: Directory to store the backup
        backup_name: Optional backup filename (default: auto-generated)
        
    Returns:
        Path to the backup file
    """
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if backup_name is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{db_path.stem}_{timestamp}.sqlite"
    
    backup_path = backup_dir / backup_name
    
    # Use SQLite backup API for consistency
    source_conn = sqlite3.connect(str(db_path))
    backup_conn = sqlite3.connect(str(backup_path))
    source_conn.backup(backup_conn)
    backup_conn.close()
    source_conn.close()
    
    return backup_path


def restore_database(backup_path: Path, target_path: Path) -> None:
    """Restore a database from a backup.
    
    Args:
        backup_path: Path to the backup file
        target_path: Path to restore to
    """
    backup_path = Path(backup_path)
    target_path = Path(target_path)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    
    # Use SQLite backup API for consistency
    backup_conn = sqlite3.connect(str(backup_path))
    target_conn = sqlite3.connect(str(target_path))
    backup_conn.backup(target_conn)
    target_conn.close()
    backup_conn.close()


def run_integrity_check(project_path: Path) -> tuple[bool, Optional[str]]:
    """Run PRAGMA integrity_check on a project database.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Tuple of (is_ok, error_message)
        - is_ok: True if integrity check passed
        - error_message: Error message if check failed, None if passed
    """
    project_path = Path(project_path)
    project_db = project_path / "project.sqlite"
    
    if not project_db.exists():
        return False, "Database file not found"
    
    try:
        conn = sqlite3.connect(str(project_db))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        
        if result == "ok":
            return True, None
        else:
            return False, result
    except Exception as e:
        return False, str(e)
