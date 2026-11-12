"""Tests for project file management."""

import pytest
import os
from pathlib import Path
from uuid import uuid4

from litfoundry.project_files import WriteOnceFileHelper, StagedProvisioning


class TestWriteOnceFileHelper:
    """Tests for write-once file semantics."""
    
    def test_write_bytes(self, tmp_path):
        """Test writing bytes to a file."""
        target = tmp_path / "test.txt"
        data = b"Hello, World!"
        
        WriteOnceFileHelper.write_bytes(target, data)
        
        assert target.exists()
        assert target.read_bytes() == data
    
    def test_write_text(self, tmp_path):
        """Test writing text to a file."""
        target = tmp_path / "test.txt"
        text = "Hello, World!"
        
        WriteOnceFileHelper.write_text(target, text)
        
        assert target.exists()
        assert target.read_text() == text
    
    def test_write_bytes_creates_parent_dirs(self, tmp_path):
        """Test that write creates parent directories."""
        target = tmp_path / "deep" / "nested" / "path" / "file.txt"
        data = b"content"
        
        WriteOnceFileHelper.write_bytes(target, data)
        
        assert target.exists()
        assert target.read_bytes() == data
    
    def test_write_bytes_no_temp_file_on_success(self, tmp_path):
        """Test that no .tmp file is left on successful write."""
        target = tmp_path / "test.txt"
        data = b"content"
        
        WriteOnceFileHelper.write_bytes(target, data)
        
        # Check no .tmp files exist
        tmp_files = list(tmp_path.glob("**/.tmp-*"))
        assert len(tmp_files) == 0
    
    def test_write_file_from_stream(self, tmp_path):
        """Test writing from a stream."""
        source_data = b"Test data from stream"
        source_file = tmp_path / "source.txt"
        source_file.write_bytes(source_data)
        
        target = tmp_path / "target.txt"
        
        with open(source_file, 'rb') as stream:
            bytes_written = WriteOnceFileHelper.write_file_from_stream(target, stream)
        
        assert bytes_written == len(source_data)
        assert target.read_bytes() == source_data


class TestStagedProvisioning:
    """Tests for staged project provisioning."""
    
    def test_create_staging_folder(self, tmp_path):
        """Test creating a staging folder."""
        project_id = str(uuid4())
        staging_path = StagedProvisioning.create_staging_folder(tmp_path, project_id)
        
        assert staging_path.exists()
        assert staging_path.name == f".staging-{project_id}"
        assert staging_path.parent == tmp_path / "projects"
    
    def test_create_staging_folder_already_exists(self, tmp_path):
        """Test error when staging folder already exists."""
        project_id = str(uuid4())
        
        # Create first staging folder
        StagedProvisioning.create_staging_folder(tmp_path, project_id)
        
        # Try to create again - should fail
        with pytest.raises(IOError):
            StagedProvisioning.create_staging_folder(tmp_path, project_id)
    
    def test_commit_staging_folder(self, tmp_path):
        """Test committing a staging folder."""
        project_id = str(uuid4())
        
        # Create staging folder
        staging_path = StagedProvisioning.create_staging_folder(tmp_path, project_id)
        
        # Create a test file in staging
        (staging_path / "test.txt").write_text("test")
        
        # Commit
        final_path = StagedProvisioning.commit_staging_folder(tmp_path, project_id)
        
        assert final_path.exists()
        assert final_path.name == project_id
        assert (final_path / "test.txt").exists()
        assert not staging_path.exists()
    
    def test_cleanup_staging_folder(self, tmp_path):
        """Test cleaning up a staging folder on failure."""
        project_id = str(uuid4())
        
        # Create staging folder
        staging_path = StagedProvisioning.create_staging_folder(tmp_path, project_id)
        
        # Cleanup
        StagedProvisioning.cleanup_staging_folder(tmp_path, project_id)
        
        assert not staging_path.exists()
    
    def test_cleanup_nonexistent_staging_folder(self, tmp_path):
        """Test that cleanup doesn't fail on nonexistent folder."""
        project_id = str(uuid4())
        
        # Should not raise
        StagedProvisioning.cleanup_staging_folder(tmp_path, project_id)
    
    def test_create_project_subdirectories(self, tmp_path):
        """Test creating project subdirectories."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        StagedProvisioning.create_project_subdirectories(project_path)
        
        # Check all subdirectories exist
        expected_dirs = ["sources", "imports", "attachments", "figures", "reports", "exports", "temp"]
        for subdir in expected_dirs:
            assert (project_path / subdir).exists()
