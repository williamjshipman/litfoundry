"""Path containment and UUID naming tests."""

import tempfile
from pathlib import Path

import pytest

from litfoundry.filesystem import (
    generate_uuid_name,
    generate_uuid_path,
    validate_contained_path,
)


class TestPathContainment:
    """Path containment validation tests."""

    def test_valid_relative_path(self):
        """Test that valid relative paths are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path("projects") / "project1"

            resolved = validate_contained_path(base, requested)
            assert resolved == base / requested

    def test_valid_nested_path(self):
        """Test that nested relative paths are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path("projects") / "abc123" / "records" / "file.json"

            resolved = validate_contained_path(base, requested)
            assert resolved == base / requested

    def test_reject_parent_directory_escape(self):
        """Test that .. escapes are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path("projects") / ".." / ".." / "etc" / "passwd"

            with pytest.raises(ValueError, match=".."):
                validate_contained_path(base, requested)

    def test_reject_single_parent_reference(self):
        """Test that .. at start is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path("..") / "etc" / "passwd"

            with pytest.raises(ValueError, match=".."):
                validate_contained_path(base, requested)

    def test_reject_absolute_path(self):
        """Test that absolute paths are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path("/etc/passwd")

            with pytest.raises(ValueError, match="Absolute paths"):
                validate_contained_path(base, requested)

    def test_reject_symlink_escaping(self):
        """Test that symlinks escaping the root are rejected."""
        import tempfile as tmpmod
        
        # Create two separate temp directories to ensure symlink target is outside
        with tmpmod.TemporaryDirectory() as tmpdir_base:
            base_parent = Path(tmpdir_base)
            # Create data root inside
            base = base_parent / "dataroot"
            base.mkdir()
            
            # Create file outside the data root
            outside = base_parent / "outside.txt"
            outside.write_text("secret")

            # Create a directory inside base
            inside_dir = base / "inside"
            inside_dir.mkdir()

            # Create a symlink inside that points outside the data root
            symlink = inside_dir / "link_outside"
            try:
                symlink.symlink_to(outside)
            except OSError:
                # Symlinks may not be available on all Windows systems
                pytest.skip("Symlinks not available on this system")

            # Try to resolve through the symlink
            requested = Path("inside") / "link_outside"

            with pytest.raises(ValueError, match="escapes data root"):
                validate_contained_path(base, requested)

    def test_valid_symlink_inside_root(self):
        """Test that symlinks within the root are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Create target directory inside base
            target_dir = base / "target"
            target_dir.mkdir()

            # Create a subdirectory with a symlink to target
            subdir = base / "subdir"
            subdir.mkdir()
            symlink = subdir / "link_to_target"
            symlink.symlink_to(target_dir)

            # Resolve through the symlink
            requested = Path("subdir") / "link_to_target"

            resolved = validate_contained_path(base, requested)
            # Should resolve to target_dir
            assert resolved == target_dir

    def test_path_with_single_dot(self):
        """Test that . (current directory) is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path(".") / "projects" / "project1"

            resolved = validate_contained_path(base, requested)
            # Should resolve to projects/project1
            assert "projects" in resolved.parts

    def test_empty_path_resolves_to_root(self):
        """Test that empty relative path resolves to root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path(".")

            resolved = validate_contained_path(base, requested)
            assert resolved == base

    def test_nonexistent_path_ok_if_contained(self):
        """Test that nonexistent paths are OK if they're contained."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            requested = Path("projects") / "nonexistent" / "file.json"

            # Should not raise; path doesn't need to exist
            resolved = validate_contained_path(base, requested)
            assert resolved == base / requested


class TestUUIDGeneration:
    """UUID-based naming tests."""

    def test_generate_uuid_name(self):
        """Test that UUID names are generated."""
        name = generate_uuid_name()

        # Should be a string
        assert isinstance(name, str)
        # Should be hex characters only (no dashes)
        assert all(c in "0123456789abcdef" for c in name)
        # Should be reasonable length (UUID4 is 32 hex chars)
        assert len(name) == 32

    def test_uuid_names_are_unique(self):
        """Test that generated UUIDs are unique."""
        names = set(generate_uuid_name() for _ in range(100))
        # All 100 should be unique
        assert len(names) == 100

    def test_generate_uuid_path(self):
        """Test that UUID paths are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = generate_uuid_path(base)

            # Should be under base
            assert str(path).startswith(str(base))
            # Name part should be a UUID
            name_part = path.name
            assert all(c in "0123456789abcdef" for c in name_part)

    def test_uuid_paths_are_unique(self):
        """Test that generated paths have unique names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            paths = set(generate_uuid_path(base) for _ in range(10))
            # All 10 should have different names
            assert len(paths) == 10

    def test_uuid_path_names_only(self):
        """Test that UUID paths don't contain user input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = generate_uuid_path(base)

            # Name should not contain any special characters except hex
            name = path.name
            # No slashes, no dots, no .. etc
            assert "/" not in name
            assert "\\" not in name
            assert ".." not in name
            assert "." not in name


class TestPathContainmentIntegration:
    """Integration tests for path containment."""

    def test_real_project_structure(self):
        """Test realistic project directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Create realistic project structure
            project_id = generate_uuid_name()
            project_dir = base / "projects" / project_id
            project_dir.mkdir(parents=True)

            records_dir = project_dir / "records"
            records_dir.mkdir()

            # Should be able to resolve records path
            requested = Path("projects") / project_id / "records"
            resolved = validate_contained_path(base, requested)
            assert resolved == records_dir

    def test_cannot_escape_via_crafted_path(self):
        """Test that even crafted paths cannot escape."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Try various escape attempts
            attempts = [
                Path("projects") / ".." / ".." / ".." / "etc" / "passwd",
                Path("..") / "..&" / "..&" / "secret",
                Path("projects") / "../../secret",
            ]

            for attempt in attempts:
                with pytest.raises(ValueError):
                    validate_contained_path(base, attempt)
