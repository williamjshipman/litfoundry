"""Product constants and metadata."""


class ProductConstants:
    """LitFoundry product constants."""

    NAME = "LitFoundry"
    TAGLINE = "Systematic literature reviews, PRISMA workflows, and bibliometric analysis"
    DESCRIPTION = (
        "LitFoundry is an open-source application for managing literature reviews "
        "with PRISMA compliance."
    )
    VERSION = "1.0.0"

    # Process names
    SERVER_PROCESS_NAME = "litfoundry-server"
    WORKER_PROCESS_NAME = "litfoundry-worker"

    @classmethod
    def get_about_text(cls) -> str:
        """Get the About screen text."""
        return f"{cls.NAME}\n{cls.TAGLINE}\n\nVersion {cls.VERSION}"
