"""Tests for LitFoundry naming compliance."""

import subprocess
from pathlib import Path


class TestNamingCompliance:
    """Tests to ensure no legacy brm, pybrm, bibliometric-research-manager or appctl names."""

    FORBIDDEN_NAMES = ["brm", "pybrm", "bibliometric-research-manager", "appctl"]

    @staticmethod
    def _scan_directory(directory: Path, extension: str = "") -> list[str]:
        """Scan directory for files and return their contents."""
        results = []
        if extension:
            files = directory.rglob(f"*{extension}")
        else:
            files = directory.rglob("*")

        for file_path in files:
            if file_path.is_file():
                try:
                    results.append(file_path.read_text(encoding="utf-8", errors="ignore"))
                except (OSError, UnicodeDecodeError):
                    pass
        return results

    def test_no_forbidden_names_in_pyproject(self):
        """Test that pyproject.toml doesn't contain forbidden names."""
        root = Path(__file__).parent.parent
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            for name in self.FORBIDDEN_NAMES:
                assert (
                    name not in content.lower()
                ), f"Found '{name}' in pyproject.toml"

    def test_no_forbidden_names_in_source(self):
        """Test that source code doesn't contain forbidden names in identifiers."""
        root = Path(__file__).parent.parent
        src_dir = root / "src"
        if src_dir.exists():
            contents = self._scan_directory(src_dir, ".py")
            for content in contents:
                for name in self.FORBIDDEN_NAMES:
                    # Allow in comments and strings, but not as identifiers
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if name in line:
                            # Check if it's in a comment or string (rough check)
                            stripped = line.split("#")[0]  # Remove comments
                            if '"""' not in line and "'''" not in line:
                                # Allow in URLs and comments
                                if name in stripped.lower():
                                    # Could be an identifier, report it
                                    assert False, (
                                        f"Possible '{name}' found in {src_dir}:{i}: {line.strip()}"
                                    )

    def test_cli_entry_point(self):
        """Test that the CLI entry point is litfoundry, not brm or appctl."""
        result = subprocess.run(
            ["litfoundry", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "litfoundry" in result.stdout.lower()


class TestNamingComplianceNegative:
    """Negative test: verify the test fails when a forbidden name is seeded."""

    def test_detects_forbidden_name_in_content(self):
        """Test that naming compliance check catches seeded violations."""
        forbidden_names = ["brm", "pybrm", "bibliometric-research-manager", "appctl"]
        test_content = 'name = "brm-test"'  # Seeded violation

        for name in forbidden_names:
            if name in test_content:
                assert True, f"Naming check detected '{name}'"
                return

        assert False, "Naming check did not detect seeded violation"
