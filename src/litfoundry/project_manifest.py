"""Project manifest management."""

import json
from pathlib import Path
from typing import Optional

from litfoundry.project_files import WriteOnceFileHelper


class ProjectManifest:
    """Manages project manifest.json files."""
    
    @staticmethod
    def create_manifest(
        project_path: Path,
        project_id: str,
        schema_version: int,
        product: str = "litfoundry"
    ) -> dict:
        """Create and write a project manifest file.
        
        The manifest contains:
        - product: Product identifier ("litfoundry")
        - uuid: Project UUID
        - schema_version: Project database schema version
        
        No secrets or absolute paths are included.
        
        Args:
            project_path: Path to the project folder
            project_id: Project UUID
            schema_version: Current project schema version
            product: Product identifier
            
        Returns:
            The manifest dictionary
            
        Raises:
            IOError: If manifest creation fails
        """
        manifest = {
            "product": product,
            "uuid": project_id,
            "schema_version": schema_version
        }
        
        manifest_path = project_path / "manifest.json"
        manifest_json = json.dumps(manifest, indent=2)
        
        WriteOnceFileHelper.write_text(
            manifest_path,
            manifest_json,
            encoding='utf-8',
            project_path=project_path
        )
        
        return manifest
    
    @staticmethod
    def read_manifest(project_path: Path) -> dict:
        """Read a project manifest file.
        
        Args:
            project_path: Path to the project folder
            
        Returns:
            The manifest dictionary
            
        Raises:
            FileNotFoundError: If manifest not found
            json.JSONDecodeError: If manifest is malformed
        """
        manifest_path = project_path / "manifest.json"
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        return manifest
    
    @staticmethod
    def validate_manifest(manifest: dict, expected_project_id: Optional[str] = None) -> bool:
        """Validate a manifest dictionary.
        
        Args:
            manifest: The manifest to validate
            expected_project_id: Optional UUID to verify matches
            
        Returns:
            True if manifest is valid
            
        Raises:
            ValueError: If manifest is invalid
        """
        # Check required fields
        required_fields = ["product", "uuid", "schema_version"]
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Missing required field: {field}")
        
        # Check product identifier
        if manifest["product"] != "litfoundry":
            raise ValueError(f"Invalid product: {manifest['product']}")
        
        # Check UUID format
        from uuid import UUID
        try:
            UUID(manifest["uuid"])
        except ValueError:
            raise ValueError(f"Invalid UUID: {manifest['uuid']}")
        
        # Check schema version
        if not isinstance(manifest["schema_version"], int) or manifest["schema_version"] < 1:
            raise ValueError(f"Invalid schema version: {manifest['schema_version']}")
        
        # Check expected project ID if provided
        if expected_project_id and manifest["uuid"] != expected_project_id:
            raise ValueError(
                f"Project ID mismatch: manifest has {manifest['uuid']}, expected {expected_project_id}"
            )
        
        # Check for secrets or absolute paths
        manifest_json = json.dumps(manifest)
        if "://" in manifest_json and "sqlite://" not in manifest_json:
            raise ValueError("Manifest should not contain absolute paths or URLs")
        
        return True
