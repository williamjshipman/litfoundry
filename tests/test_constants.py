"""Tests for product constants."""

from litfoundry.constants import ProductConstants


class TestProductConstants:
    """Product constants tests."""

    def test_name(self):
        """Test product name."""
        assert ProductConstants.NAME == "LitFoundry"

    def test_version(self):
        """Test version."""
        assert ProductConstants.VERSION == "1.0.0"

    def test_process_names(self):
        """Test process names."""
        assert ProductConstants.SERVER_PROCESS_NAME == "litfoundry-server"
        assert ProductConstants.WORKER_PROCESS_NAME == "litfoundry-worker"

    def test_about_text(self):
        """Test about text generation."""
        about = ProductConstants.get_about_text()
        assert "LitFoundry" in about
        assert "1.0.0" in about
        assert "PRISMA" in about
