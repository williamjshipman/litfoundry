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
    
    # Ensure parent directory exists
    catalog_path = Path(catalog_path)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert path to absolute and use forward slashes for SQLite URL
    # SQLite URL format: sqlite:///path (forward slashes on all platforms)
    abs_path = catalog_path.resolve()
    posix_path = abs_path.as_posix()
    db_url = f"sqlite:///{posix_path}"
    
    # Create the engine with SQLite
    engine = create_engine(
        db_url,
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
    import sqlite3
    
    # Ensure catalog parent directory exists
    catalog_path = Path(catalog_path)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    # Create tables directly - bypass Alembic due to Windows path issues
    # This is the baseline migration from 001_baseline.py
    conn = sqlite3.connect(str(catalog_path))
    try:
        cursor = conn.cursor()
        
        # Create alembic version tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                PRIMARY KEY (version_num)
            )
        """)
        
        # Check if baseline already applied
        cursor.execute("SELECT version_num FROM alembic_version WHERE version_num = '001_baseline'")
        already_applied = cursor.fetchone() is not None
        
        if not already_applied:
            # Create baseline tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    version INTEGER NOT NULL,
                    schema_name VARCHAR NOT NULL,
                    last_updated DATETIME NOT NULL,
                    PRIMARY KEY (schema_name)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key VARCHAR NOT NULL,
                    value TEXT,
                    last_updated DATETIME NOT NULL,
                    PRIMARY KEY (key)
                )
            """)
            cursor.execute(
                "INSERT INTO schema_meta (version, schema_name, last_updated) "
                "VALUES (1, 'litfoundry', CURRENT_TIMESTAMP)"
            )
            cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('001_baseline')")
        
        conn.commit()
    finally:
        conn.close()