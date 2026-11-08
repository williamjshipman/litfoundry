"""Tests for project manifest management."""

import pytest
import json
from pathlib import Path
from uuid import uuid4

from litfoundry.project_manifest import ProjectManifest


class TestProjectManifest:
    """Tests for project manifest creation and validation."""
    
    def test_create_manifest(self, tmp_path):
        """Test creating a project manifest."""
        project_id = str(uuid4())
        schema_version = 1
        
        manifest = ProjectManifest.create_manifest(tmp_path, project_id, schema_version)
        
        assert manifest["product"] == "litfoundry"
        assert manifest["uuid"] == project_id
        assert manifest["schema_version"] == schema_version
        
        # Verify file was written
        manifest_file = tmp_path / "manifest.json"
        assert manifest_file.exists()
        
        # Verify file content
        with open(manifest_file) as f:
            loaded = json.load(f)
        assert loaded == manifest
    
    def test_read_manifest(self, tmp_path):
        """Test reading a manifest file."""
        project_id = str(uuid4())
        
        # Create manifest
        created = ProjectManifest.create_manifest(tmp_path, project_id, 1)
        
        # Read manifest
        loaded = ProjectManifest.read_manifest(tmp_path)
        
        assert loaded == created
    
    def test_read_manifest_not_found(self, tmp_path):
        """Test reading a nonexistent manifest."""
        with pytest.raises(FileNotFoundError):
            ProjectManifest.read_manifest(tmp_path)
    
    def test_read_manifest_invalid_json(self, tmp_path):
        """Test reading a malformed manifest."""
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text("not valid json {")
        
        with pytest.raises(json.JSONDecodeError):
            ProjectManifest.read_manifest(tmp_path)
    
    def test_validate_manifest(self):
        """Test manifest validation."""
        project_id = str(uuid4())
        manifest = {
            "product": "litfoundry",
            "uuid": project_id,
            "schema_version": 1
        }
        
        # Should validate successfully
        assert ProjectManifest.validate_manifest(manifest) is True
    
    def test_validate_manifest_missing_fields(self):
        """Test validation with missing fields."""
        # Missing uuid
        manifest = {
            "product": "litfoundry",
            "schema_version": 1
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            ProjectManifest.validate_manifest(manifest)
    
    def test_validate_manifest_invalid_product(self):
        """Test validation with invalid product."""
        project_id = str(uuid4())
        manifest = {
            "product": "invalid",
            "uuid": project_id,
            "schema_version": 1
        }
        
        with pytest.raises(ValueError, match="Invalid product"):
            ProjectManifest.validate_manifest(manifest)
    
    def test_validate_manifest_invalid_uuid(self):
        """Test validation with invalid UUID."""
        manifest = {
            "product": "litfoundry",
            "uuid": "not-a-uuid",
            "schema_version": 1
        }
        
        with pytest.raises(ValueError, match="Invalid UUID"):
            ProjectManifest.validate_manifest(manifest)
    
    def test_validate_manifest_invalid_schema_version(self):
        """Test validation with invalid schema version."""
        project_id = str(uuid4())
        manifest = {
            "product": "litfoundry",
            "uuid": project_id,
            "schema_version": 0  # Invalid: must be >= 1
        }
        
        with pytest.raises(ValueError, match="Invalid schema version"):
            ProjectManifest.validate_manifest(manifest)
    
    def test_validate_manifest_uuid_mismatch(self):
        """Test validation with UUID mismatch."""
        project_id = str(uuid4())
        other_id = str(uuid4())
        manifest = {
            "product": "litfoundry",
            "uuid": project_id,
            "schema_version": 1
        }
        
        with pytest.raises(ValueError, match="Project ID mismatch"):
            ProjectManifest.validate_manifest(manifest, expected_project_id=other_id)
    
    def test_validate_manifest_no_absolute_paths(self):
        """Test that manifests should not contain absolute paths."""
        project_id = str(uuid4())
        manifest = {
            "product": "litfoundry",
            "uuid": project_id,
            "schema_version": 1,
            "data_path": "/absolute/path/to/data"  # Not allowed
        }
        
        with pytest.raises(ValueError, match="absolute paths"):
            ProjectManifest.validate_manifest(manifest)
