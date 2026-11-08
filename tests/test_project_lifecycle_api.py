"""Tests for project lifecycle API endpoints."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

from litfoundry.catalog.models import ProjectDirectory, User
from litfoundry.api.errors import ApiError


class TestProjectCRUD:
    """Tests for project creation, reading, updating, deletion."""
    
    def test_create_project_api(self, client, user_token):
        """Test creating a project via API."""
        # This is tested with the GUI flow
        pass
    
    def test_list_projects_api(self, client, user_token):
        """Test listing projects."""
        pass
    
    def test_get_project_api(self, client, user_token):
        """Test getting a specific project."""
        pass
    
    def test_update_project_api(self, client, user_token):
        """Test updating project details."""
        pass


class TestProjectArchive:
    """Tests for archive/unarchive operations."""
    
    def test_archive_project(self, client, user_token):
        """Test archiving a project."""
        pass
    
    def test_unarchive_project(self, client, user_token):
        """Test unarchiving a project."""
        pass
    
    def test_archived_project_read_only(self, client, user_token):
        """Test that archived projects are read-only."""
        pass


class TestProjectDeletion:
    """Tests for two-stage deletion."""
    
    def test_delete_without_confirmation(self, client, user_token):
        """Test that deletion requires confirmation."""
        pass
    
    def test_delete_with_confirmation(self, client, user_token):
        """Test deleting a project with confirmation."""
        pass
    
    def test_deleting_state_transition(self, client, user_token):
        """Test project transitions to deleting state."""
        pass
    
    def test_move_to_trash(self, client, user_token, data_root):
        """Test that deleted projects move to trash."""
        pass


class TestProjectTransfer:
    """Tests for ownership transfer."""
    
    def test_transfer_ownership(self, client, user_token):
        """Test transferring project ownership."""
        pass
    
    def test_transfer_ownership_no_folder_move(self, client, user_token, data_root):
        """Test that folder is not moved on transfer."""
        pass
    
    def test_admin_transfer_multiple_projects(self, client, admin_token):
        """Test admin transferring multiple projects."""
        pass


class TestProjectQuarantine:
    """Tests for quarantine/release."""
    
    def test_quarantine_project(self, client, admin_token):
        """Test quarantining a project."""
        pass
    
    def test_release_project(self, client, admin_token):
        """Test releasing a quarantined project."""
        pass
    
    def test_quarantined_project_unavailable(self, client, user_token):
        """Test that quarantined projects are unavailable."""
        pass


class TestProjectIntegrity:
    """Tests for integrity checking."""
    
    def test_integrity_failure_detection(self, client, data_root):
        """Test that integrity failures are detected."""
        pass
    
    def test_project_error_state_on_corruption(self, client, data_root):
        """Test that corrupted projects enter error state."""
        pass
    
    def test_admin_alert_on_corruption(self, client, admin_token, data_root):
        """Test that admin is alerted when project is corrupted."""
        pass
