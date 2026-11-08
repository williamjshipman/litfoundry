"""Tests for project migrations and schema management."""

import pytest
import tempfile
from pathlib import Path
from uuid import uuid4
import sqlite3

from litfoundry.project_migrations import (
    create_project_engine,
    run_alembic_upgrade_project,
    create_project_database,
    get_project_schema_version,
    get_latest_project_schema_version,
    backup_database,
    restore_database,
    run_integrity_check,
)


class TestProjectEngine:
    """Tests for project database engines."""
    
    def test_create_project_engine(self, tmp_path):
        """Test creating a project engine."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        engine = create_project_engine(project_path)
        assert engine is not None
        
        # Verify database file was created
        project_db = project_path / "project.sqlite"
        assert project_db.exists()
        
        # Clean up
        engine.dispose()
    
    def test_engine_has_pragmas(self, tmp_path):
        """Test that engine applies SQLite pragmas."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        engine = create_project_engine(project_path)
        
        with engine.connect() as conn:
            # Check WAL mode
            result = conn.execute("PRAGMA journal_mode").scalar()
            assert result.lower() == "wal"
            
            # Check foreign keys
            result = conn.execute("PRAGMA foreign_keys").scalar()
            assert result == 1
            
            # Check busy timeout
            result = conn.execute("PRAGMA busy_timeout").scalar()
            assert result == 5000
        
        engine.dispose()


class TestProjectMigrations:
    """Tests for project database migrations."""
    
    def test_create_project_database(self, tmp_path):
        """Test creating a new project database."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        # Create database
        create_project_database(project_path)
        
        # Verify database exists and has proper schema
        project_db = project_path / "project.sqlite"
        assert project_db.exists()
        
        # Check alembic_version table
        conn = sqlite3.connect(str(project_db))
        cursor = conn.cursor()
        cursor.execute("SELECT version_num FROM alembic_version")
        versions = cursor.fetchall()
        assert len(versions) > 0
        conn.close()
    
    def test_get_project_schema_version(self, tmp_path):
        """Test getting project schema version."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        # New project should be at version 1
        create_project_database(project_path)
        version = get_project_schema_version(project_path)
        assert version == 1
    
    def test_get_latest_schema_version(self):
        """Test getting the latest project schema version."""
        version = get_latest_project_schema_version()
        assert version >= 1


class TestDatabaseBackupRestore:
    """Tests for database backup and restoration."""
    
    def test_backup_database(self, tmp_path):
        """Test backing up a database."""
        # Create a test database
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES ('test')")
        conn.commit()
        conn.close()
        
        # Backup the database
        backup_dir = tmp_path / "backups"
        backup_path = backup_database(db_path, backup_dir)
        
        assert backup_path.exists()
        assert backup_path.parent == backup_dir
    
    def test_restore_database(self, tmp_path):
        """Test restoring a database from backup."""
        # Create a test database with data
        db_path = tmp_path / "test.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES ('original')")
        conn.commit()
        conn.close()
        
        # Create backup
        backup_dir = tmp_path / "backups"
        backup_path = backup_database(db_path, backup_dir)
        
        # Modify the original database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM test")
        conn.commit()
        conn.close()
        
        # Restore from backup
        restore_database(backup_path, db_path)
        
        # Verify data was restored
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM test")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        assert result[0] == "original"


class TestIntegrityCheck:
    """Tests for database integrity checking."""
    
    def test_integrity_check_valid_database(self, tmp_path):
        """Test integrity check on a valid database."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        create_project_database(project_path)
        
        is_ok, error = run_integrity_check(project_path)
        assert is_ok
        assert error is None
    
    def test_integrity_check_missing_database(self, tmp_path):
        """Test integrity check on missing database."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        is_ok, error = run_integrity_check(project_path)
        assert not is_ok
        assert error is not None
