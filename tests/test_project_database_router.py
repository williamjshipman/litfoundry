"""Tests for project database routing."""

import pytest
from pathlib import Path
from uuid import uuid4

from litfoundry.project_database_router import ProjectDatabaseRouter
from litfoundry.project_migrations import create_project_database


class TestProjectDatabaseRouter:
    """Tests for project database routing."""
    
    def test_router_initialization(self, tmp_path):
        """Test initializing a router."""
        router = ProjectDatabaseRouter(tmp_path)
        
        assert router.data_root == tmp_path
        assert len(router._engine_cache) == 0
    
    def test_resolve_project_path_valid_uuid(self, tmp_path):
        """Test resolving a valid project UUID."""
        router = ProjectDatabaseRouter(tmp_path)
        project_id = str(uuid4())
        
        path = router.resolve_project_path(project_id)
        
        assert path.name == project_id
        assert "projects" in path.parts
    
    def test_resolve_project_path_invalid_uuid(self, tmp_path):
        """Test resolving an invalid UUID."""
        router = ProjectDatabaseRouter(tmp_path)
        
        with pytest.raises(ValueError, match="Invalid project UUID"):
            router.resolve_project_path("not-a-uuid")
    
    def test_resolve_project_path_directory_traversal_attempt(self, tmp_path):
        """Test that directory traversal attempts are blocked."""
        router = ProjectDatabaseRouter(tmp_path)
        
        # Try to traverse outside data root
        # This should fail containment check
        # Note: The UUID validation will catch this first
        with pytest.raises(ValueError):
            router.resolve_project_path("../../../etc/passwd")
    
    def test_open_project_database(self, tmp_path):
        """Test opening a project database."""
        project_id = str(uuid4())
        project_path = tmp_path / "projects" / project_id
        project_path.mkdir(parents=True)
        
        # Create project database
        create_project_database(project_path)
        
        # Open project
        router = ProjectDatabaseRouter(tmp_path)
        session = router.open(project_id)
        
        assert session is not None
        
        # Session should be usable
        from sqlalchemy import text
        result = session.execute(text("SELECT 1"))
        assert result is not None
        
        session.close()
    
    def test_open_nonexistent_project(self, tmp_path):
        """Test opening a nonexistent project."""
        project_id = str(uuid4())
        router = ProjectDatabaseRouter(tmp_path)
        
        with pytest.raises(ValueError, match="not found"):
            router.open(project_id)
    
    def test_engine_caching(self, tmp_path):
        """Test that engines are cached."""
        project_id = str(uuid4())
        project_path = tmp_path / "projects" / project_id
        project_path.mkdir(parents=True)
        create_project_database(project_path)
        
        router = ProjectDatabaseRouter(tmp_path)
        
        # Open project twice
        session1 = router.open(project_id)
        session2 = router.open(project_id)
        
        # Both sessions should work
        from sqlalchemy import text
        session1.execute(text("SELECT 1"))
        session2.execute(text("SELECT 1"))
        
        session1.close()
        session2.close()
        
        # Verify caching
        assert project_id in router._engine_cache
    
    def test_lru_cache_eviction(self, tmp_path):
        """Test that LRU cache evicts old engines."""
        router = ProjectDatabaseRouter(tmp_path)
        router._max_cached_engines = 3
        
        # Create and open multiple projects
        project_ids = []
        for i in range(5):
            project_id = str(uuid4())
            project_path = tmp_path / "projects" / project_id
            project_path.mkdir(parents=True)
            create_project_database(project_path)
            
            session = router.open(project_id)
            session.close()
            project_ids.append(project_id)
        
        # Cache should not exceed max size
        assert len(router._engine_cache) <= router._max_cached_engines
        
        # First projects should be evicted
        assert project_ids[0] not in router._engine_cache
        assert project_ids[1] not in router._engine_cache
        
        # Last projects should be cached
        assert project_ids[3] in router._engine_cache or project_ids[4] in router._engine_cache
    
    def test_close_all_engines(self, tmp_path):
        """Test closing all cached engines."""
        project_id = str(uuid4())
        project_path = tmp_path / "projects" / project_id
        project_path.mkdir(parents=True)
        create_project_database(project_path)
        
        router = ProjectDatabaseRouter(tmp_path)
        session = router.open(project_id)
        session.close()
        
        # Cache should have the engine
        assert len(router._engine_cache) > 0
        
        # Close all
        router.close_all()
        
        # Cache should be empty
        assert len(router._engine_cache) == 0
