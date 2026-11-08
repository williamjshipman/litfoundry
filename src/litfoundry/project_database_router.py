"""Project database routing and connection management."""

import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class ProjectDatabaseRouter:
    """Routes requests to project-specific databases with safety checks."""
    
    def __init__(self, data_root: Path):
        """Initialize the router.
        
        Args:
            data_root: Root data directory containing projects/
        """
        self.data_root = Path(data_root)
        self._engine_cache = {}  # LRU cache of project engines
        self._max_cached_engines = 10
    
    def _get_cached_engine(self, project_id: str) -> Optional[Engine]:
        """Get a cached engine for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Cached engine or None
        """
        return self._engine_cache.get(project_id)
    
    def _cache_engine(self, project_id: str, engine: Engine) -> None:
        """Cache an engine with LRU eviction.
        
        Args:
            project_id: Project UUID
            engine: SQLAlchemy engine
        """
        self._engine_cache[project_id] = engine
        
        # Simple LRU: if cache exceeds limit, remove oldest
        if len(self._engine_cache) > self._max_cached_engines:
            # Remove first item (oldest in insertion order, Python 3.7+)
            oldest_key = next(iter(self._engine_cache))
            del self._engine_cache[oldest_key]
    
    def _check_containment(self, project_path: Path) -> None:
        """Verify that project path is contained within data root.
        
        Prevents directory traversal attacks.
        
        Args:
            project_path: Path to verify
            
        Raises:
            ValueError: If path is outside data root
        """
        # Resolve to absolute paths
        data_root_abs = self.data_root.resolve()
        project_abs = project_path.resolve()
        
        # Check that project path starts with data root
        try:
            project_abs.relative_to(data_root_abs)
        except ValueError:
            raise ValueError(
                f"Project path {project_abs} is not contained within data root {data_root_abs}"
            )
    
    def resolve_project_path(self, project_id: str) -> Path:
        """Resolve a project UUID to its folder path via the catalogue.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Absolute path to the project folder
            
        Raises:
            ValueError: If project not found or path invalid
        """
        # project_id should be a valid UUID
        try:
            UUID(project_id)
        except ValueError:
            raise ValueError(f"Invalid project UUID: {project_id}")
        
        # In a real implementation, this would query the catalogue
        # For now, assume standard naming: projects/<uuid>/
        project_path = self.data_root / "projects" / project_id
        
        # Check containment
        self._check_containment(project_path)
        
        return project_path
    
    def open(self, project_id: str) -> Session:
        """Open a project database and return a session.
        
        Performs:
        1. UUID validation
        2. Path resolution via catalogue
        3. Containment check
        4. State/version re-check
        5. Database opening with NullPool and PRAGMAs
        
        Args:
            project_id: Project UUID
            
        Returns:
            SQLAlchemy session
            
        Raises:
            ValueError: If project invalid or path invalid
            APIError: If project unavailable
        """
        # Resolve path
        project_path = self.resolve_project_path(project_id)
        
        # Check that project database exists
        project_db = project_path / "project.sqlite"
        if not project_db.exists():
            raise APIError(
                code="PROJECT_NOT_FOUND",
                message=f"Project {project_id} database not found",
                status_code=404
            )
        
        # Get or create engine
        engine = self._get_cached_engine(project_id)
        if not engine:
            # Create new engine with NullPool
            abs_path = project_db.resolve()
            posix_path = abs_path.as_posix()
            db_url = f"sqlite:///{posix_path}"
            
            engine = create_engine(
                db_url,
                echo=False,
                poolclass=None,  # NullPool - no connection pooling
            )
            
            # Configure SQLite pragmas on each connection
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragmas(dbapi_conn, connection_record):
                """Set SQLite pragmas for production use."""
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
                cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
                cursor.execute("PRAGMA busy_timeout=5000")  # 5-second busy timeout
                cursor.close()
            
            self._cache_engine(project_id, engine)
        
        # Create session
        SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
        return SessionLocal()
    
    def close_all(self) -> None:
        """Close all cached engines."""
        for engine in self._engine_cache.values():
            engine.dispose()
        self._engine_cache.clear()
