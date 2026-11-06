"""Tests for product constants."""

from litfoundry.constants import ProductConstants


class TestProductConstants:
    """Product constants tests."""

    def test_name(self):
        """Test product name."""
        assert ProductConstants.NAME == "LitFoundry"

    def test_tagline_exact(self):
        """Test tagline matches spec exactly."""
        assert ProductConstants.TAGLINE == "From literature to insight."

    def test_description_exact(self):
        """Test description matches spec exactly."""
        expected = "Open-source software for systematic literature reviews, PRISMA workflows and bibliometric analysis."
        assert ProductConstants.DESCRIPTION == expected

    def test_license(self):
        """Test license is correct."""
        assert ProductConstants.LICENSE == "GNU GPL v3"

    def test_version(self):
        """Test version."""
        assert ProductConstants.VERSION == "1.0.0"

    def test_process_names(self):
        """Test process names."""
        assert ProductConstants.SERVER_PROCESS_NAME == "litfoundry-server"
        assert ProductConstants.WORKER_PROCESS_NAME == "litfoundry-worker"

    def test_about_text_contains_name(self):
        """Test about text contains product name."""
        about = ProductConstants.get_about_text()
        assert "LitFoundry" in about

    def test_about_text_contains_tagline(self):
        """Test about text contains exact tagline."""
        about = ProductConstants.get_about_text()
        assert "From literature to insight." in about

    def test_about_text_contains_version(self):
        """Test about text contains version."""
        about = ProductConstants.get_about_text()
        assert "1.0.0" in about

    def test_about_text_contains_license(self):
        """Test about text contains license per spec."""
        about = ProductConstants.get_about_text()
        assert "GNU GPL v3" in about

    def test_about_text_contains_admin_disclosure(self):
        """Test about text contains administrator trust disclosure."""
        about = ProductConstants.get_about_text()
        assert "Administrator Disclosure:" in about
        assert "administrator can read and change every project" in about
        assert "all stored data and credentials" in about

    def test_about_text_comprehensive(self):
        """Test about text includes all required elements."""
        about = ProductConstants.get_about_text()
        required_elements = [
            "LitFoundry",
            "From literature to insight.",
            "Version 1.0.0",
            "License: GNU GPL v3",
            "Administrator Disclosure",
        ]
        for element in required_elements:
            assert element in about, f"About text missing: {element}"
