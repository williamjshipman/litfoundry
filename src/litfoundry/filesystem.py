"""Filesystem utilities and safety checks."""

from pathlib import Path


def check_path_safety(root: Path) -> None:
    """Check that a path is safe for use."""
    # TODO: Implement path safety checks
    pass


def check_network_filesystem(root: Path) -> None:
    """Check that the path is not on a network filesystem."""
    # TODO: Implement network filesystem detection
    pass
