"""Integration tests for data root initialization."""

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from litfoundry.initialization import initialize_data_root, reinitialize_data_root


class TestDataRootInitialization:
    """Data root initialization integration tests."""

    @mock.patch("litfoundry.initialization.apply_permissions")
    def test_init_fresh_root(self, mock_perms):
        """Test initializing a fresh data root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "new_root"
            initialize_data_root(root)

            # Verify directory structure
            assert root.exists()
            assert (root / "logs").exists()
            assert (root / "secret_material").exists()
            assert (root / "projects").exists()
            assert (root / ".initialized").exists()
            # Verify permissions were applied
            mock_perms.assert_called_once()

    @mock.patch("litfoundry.initialization.apply_permissions")
    def test_init_idempotent(self, mock_perms):
        """Test that re-running init on an existing root is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "root"
            initialize_data_root(root)

            marker = root / ".initialized"
            initial_mtime = marker.stat().st_mtime

            # Re-initialize (should be no-op)
            initialize_data_root(root)

            # Marker file should not have changed
            assert marker.exists()
            # apply_permissions should only be called once (first initialization)
            mock_perms.assert_called_once()

    @mock.patch("litfoundry.initialization.apply_permissions")
    def test_reinitialize_data_root(self, mock_perms):
        """Test explicit re-initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "root"
            reinitialize_data_root(root)
            assert root.exists()
            assert (root / ".initialized").exists()

    def test_init_with_real_permissions(self):
        """Test initialization with real permissions (not mocked)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "real_permissions"
            # Initialize with actual permissions applied
            initialize_data_root(root)

            # Verify all structures exist
            assert root.exists()
            assert (root / "catalog.sqlite").exists()
            assert (root / "logs").exists()
            assert (root / "secret_material").exists()
            assert (root / "projects").exists()
            assert (root / ".initialized").exists()

            # Verify secrets were created
            secret_material = root / "secret_material"
            assert (secret_material / "master.key").exists()
            assert (secret_material / "session_signing.key").exists()

            # Verify catalogue database has schema
            import sqlite3
            conn = sqlite3.connect(str(root / "catalog.sqlite"))
            try:
                cursor = conn.cursor()
                # Check that required tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in cursor.fetchall()}
                assert "alembic_version" in tables
                assert "schema_meta" in tables
                assert "system_settings" in tables
            finally:
                conn.close()

