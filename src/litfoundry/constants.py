"""Product constants and metadata."""


class ProductConstants:
    """LitFoundry product constants."""

    NAME = "LitFoundry"
    TAGLINE = "From literature to insight."
    DESCRIPTION = (
        "Open-source software for systematic literature reviews, PRISMA workflows "
        "and bibliometric analysis."
    )
    VERSION = "1.0.0"
    LICENSE = "GNU GPL v3"

    # Process names
    SERVER_PROCESS_NAME = "litfoundry-server"
    WORKER_PROCESS_NAME = "litfoundry-worker"

    @classmethod
    def get_about_text(cls) -> str:
        """Get the About screen text with license and administrator trust disclosure."""
        admin_disclosure = (
            "Administrator Disclosure: The administrator can read and change every project "
            "and, through the server host and full backups, all stored data and credentials."
        )
        return (
            f"{cls.NAME}\n"
            f"{cls.TAGLINE}\n\n"
            f"Version {cls.VERSION}\n"
            f"License: {cls.LICENSE}\n\n"
            f"{admin_disclosure}"
        )
