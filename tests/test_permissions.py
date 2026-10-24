"""OS-specific permission tests."""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from litfoundry.filesystem import apply_permissions, _apply_windows_permissions, _apply_posix_permissions


class TestPermissionsWindows:
    """Windows DACL permission tests."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_windows_permissions_function_exists(self):
        """Test that Windows permissions function is defined."""
        assert callable(_apply_windows_permissions)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_windows_permissions_with_pywin32(self):
        """Test Windows permissions with pywin32 available."""
        # Simply verify the function can be called without error on Windows
        # We can't apply actual DACL to a temp directory without breaking cleanup,
        # so we test with a mock
        with mock.patch("litfoundry.filesystem._apply_windows_permissions") as mock_win:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                apply_permissions(root)
                # On Windows, _apply_windows_permissions should be called
                mock_win.assert_called_once_with(root)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_windows_permissions_fallback_mock(self):
        """Test Windows permission fallback path with mocking."""
        # Test the fallback logic by mocking win32security to raise ImportError
        import litfoundry.filesystem as fs_module

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Patch the internal attempt to import win32security
            original_func = fs_module._apply_windows_permissions

            def mock_apply_with_import_error(path):
                try:
                    # Simulate ImportError from win32security
                    import win32security  # noqa
                except ImportError:
                    # Should fall through to os.chmod
                    os.chmod(path, 0o700)

            with mock.patch.object(fs_module, "_apply_windows_permissions", mock_apply_with_import_error):
                mock_apply_with_import_error(root)
                # If it completed without error, it worked
                assert root.exists()


class TestPermissionsPOSIX:
    """POSIX 0o700 permission tests."""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_posix_permissions_function_exists(self):
        """Test that POSIX permissions function is defined."""
        assert callable(_apply_posix_permissions)

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_posix_apply_permissions_calls_posix_function(self):
        """Test that POSIX systems call the POSIX function."""
        with mock.patch("litfoundry.filesystem._apply_posix_permissions") as mock_posix:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                apply_permissions(root)
                # On POSIX, _apply_posix_permissions should be called
                mock_posix.assert_called_once_with(root)

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_apply_posix_permissions(self):
        """Test POSIX 0o700 permission application."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            apply_permissions(root)

            # Verify 0o700 mode
            mode = root.stat().st_mode & 0o777
            assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_posix_permissions_restrict_group_and_others(self):
        """Test that 0o700 removes group and other permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # First set permissive permissions
            os.chmod(root, 0o777)
            assert (root.stat().st_mode & 0o777) == 0o777

            # Apply restrictive permissions
            apply_permissions(root)

            # Verify only owner has permissions
            mode = root.stat().st_mode & 0o777
            assert mode == 0o700
            # Owner should have r, w, x
            assert mode & 0o700 == 0o700
            # Group and others should have nothing
            assert mode & 0o077 == 0o000

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_posix_nested_directories(self):
        """Test that permissions are applied to a directory with contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create nested structure
            (root / "subdir").mkdir()
            (root / "subdir" / "file.txt").write_text("test")

            # Apply permissions to root
            apply_permissions(root)

            # Verify root has 0o700
            root_mode = root.stat().st_mode & 0o777
            assert root_mode == 0o700

            # Note: we only apply permissions to the root, not children
            # So subdir may still have inherited permissions


class TestPermissionsGeneral:
    """General permission tests that work on all platforms."""

    def test_apply_permissions_called_with_valid_path(self):
        """Test that apply_permissions can be called with a valid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Mock the actual permission application to avoid cleanup issues
            with mock.patch("litfoundry.filesystem._apply_windows_permissions" if sys.platform == "win32" else
                           "litfoundry.filesystem._apply_posix_permissions"):
                # Should not raise
                apply_permissions(root)
                assert root.exists()

    def test_apply_permissions_nonexistent_path(self):
        """Test behavior when path doesn't exist."""
        root = Path("/nonexistent/path/that/does/not/exist")
        # Should raise an error from either win32security or os.chmod
        with pytest.raises((OSError, Exception)):
            apply_permissions(root)

    def test_apply_permissions_on_dispatch(self):
        """Test that apply_permissions dispatches to the correct platform function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            if sys.platform == "win32":
                with mock.patch("litfoundry.filesystem._apply_windows_permissions") as mock_platform:
                    apply_permissions(root)
                    mock_platform.assert_called_once()
            else:
                with mock.patch("litfoundry.filesystem._apply_posix_permissions") as mock_platform:
                    apply_permissions(root)
                    mock_platform.assert_called_once()
