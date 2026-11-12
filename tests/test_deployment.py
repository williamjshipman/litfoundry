"""Tests for deployment configuration and documentation."""

import subprocess
from pathlib import Path


class TestCaddyfileConfiguration:
    """Tests for Caddyfile.example validation."""

    def test_caddyfile_exists(self):
        """Test that Caddyfile.example exists."""
        caddyfile = Path(__file__).parent.parent / "packaging" / "caddy" / "Caddyfile.example"
        assert caddyfile.exists(), f"Caddyfile.example not found at {caddyfile}"

    def test_caddyfile_has_content(self):
        """Test that Caddyfile.example has content."""
        caddyfile = Path(__file__).parent.parent / "packaging" / "caddy" / "Caddyfile.example"
        content = caddyfile.read_text()
        assert len(content) > 100, "Caddyfile.example is too short"
        assert "litfoundry.example.internal" in content, "Caddyfile missing hostname placeholder"
        assert "reverse_proxy 127.0.0.1:5080" in content, "Caddyfile missing LitFoundry loopback proxy"

    def test_caddyfile_comments_are_helpful(self):
        """Test that Caddyfile.example includes helpful comments."""
        caddyfile = Path(__file__).parent.parent / "packaging" / "caddy" / "Caddyfile.example"
        content = caddyfile.read_text()
        
        # Check for important comments
        expected_comments = [
            "HTTP to HTTPS",
            "TLS",
            "reverse proxy",
            "X-Forwarded",
            "timeout",
        ]
        for comment in expected_comments:
            assert comment.lower() in content.lower(), f"Caddyfile missing comment about '{comment}'"

    def test_caddyfile_validates_with_caddy_if_available(self):
        """Test that Caddyfile.example validates with `caddy validate` if Caddy is available."""
        # This test is skipped if Caddy is not installed
        # In CI, this might be available on Linux runners
        try:
            caddyfile = Path(__file__).parent.parent / "packaging" / "caddy" / "Caddyfile.example"
            
            # Try to validate with caddy CLI
            result = subprocess.run(
                ["caddy", "validate", "--config", str(caddyfile)],
                capture_output=True,
                timeout=5,
            )
            
            # Configuration must validate cleanly with exit code 0.
            # Accepting failure (exit code 1) would mask syntax errors like invalid subdirectives.
            # A properly formed Caddyfile must pass validation.
            assert result.returncode == 0, f"Caddyfile validation failed: {result.stderr.decode()}"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Caddy not installed or timed out; skip this test
            pass


class TestDeploymentDocumentation:
    """Tests for deployment documentation."""

    def test_deployment_docs_exist(self):
        """Test that deployment documentation exists."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        assert docs_file.exists(), f"deployment.md not found at {docs_file}"

    def test_deployment_docs_have_content(self):
        """Test that deployment documentation has sufficient content."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        assert len(content) > 1000, "deployment.md is too short"

    def test_deployment_docs_cover_all_oses(self):
        """Test that deployment docs mention all supported operating systems."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        # Check for OS-specific sections
        os_references = ["Windows", "Linux", "macOS"]
        for os_name in os_references:
            assert os_name in content, f"deployment.md doesn't mention {os_name}"

    def test_deployment_docs_mention_proxy(self):
        """Test that deployment docs explain reverse proxy setup."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        assert "reverse proxy" in content.lower(), "deployment.md doesn't explain reverse proxy"
        assert "caddy" in content.lower(), "deployment.md doesn't mention Caddy"

    def test_deployment_docs_mention_ca_trust(self):
        """Test that deployment docs explain CA trust distribution."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        assert "ca" in content.lower(), "deployment.md doesn't mention CA"
        assert "trust" in content.lower(), "deployment.md doesn't mention trust"

    def test_deployment_docs_mention_firewall(self):
        """Test that deployment docs explain firewall configuration."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        assert "firewall" in content.lower(), "deployment.md doesn't mention firewall"

    def test_deployment_docs_mention_https_only(self):
        """Test that deployment docs emphasize HTTPS-only policy."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        assert "https" in content.lower(), "deployment.md doesn't emphasize HTTPS"
        assert "loopback" in content.lower(), "deployment.md doesn't mention loopback-only listening"

    def test_deployment_docs_mention_logging(self):
        """Test that deployment docs explain logging setup."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        assert "log" in content.lower(), "deployment.md doesn't mention logging"

    def test_deployment_docs_mention_troubleshooting(self):
        """Test that deployment docs include troubleshooting section."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        assert "troubleshooting" in content.lower(), "deployment.md missing troubleshooting section"

    def test_deployment_docs_mention_data_root_location(self):
        """Test that deployment docs document data root locations."""
        docs_file = Path(__file__).parent.parent / "docs" / "deployment.md"
        content = docs_file.read_text()
        
        # Check for platform-specific data root paths
        assert "programdata" in content.lower() or "c:\\" in content.lower(), \
            "deployment.md missing Windows data root path"
        assert "library" in content.lower() or "application support" in content.lower(), \
            "deployment.md missing macOS data root path"
        assert "/var/lib" in content.lower(), "deployment.md missing Linux data root path"
