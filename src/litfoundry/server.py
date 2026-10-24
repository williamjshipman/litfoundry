"""Server startup and management."""

import os
import sys
from pathlib import Path

from litfoundry.app import create_app
from litfoundry.config import Config


def start_server(root: Path, port: int = 5080, mode: str = "server") -> None:
    """Start the LitFoundry server with Waitress.

    Args:
        root: Path to the data root
        port: Port to listen on (default: 5080)
        mode: Execution mode: 'server' or 'workstation'

    Raises:
        ValueError: If the data root is invalid or on a network filesystem
        SystemExit: If configuration is invalid
    """
    # Validate the data root
    Config.validate_data_root(root)

    # Validate mode is set and valid
    if not mode or mode not in ("server", "workstation"):
        sys.exit(f"Error: run mode must be 'server' or 'workstation', got '{mode}'")

    # Refuse debug mode (Flask debug should never run in serve)
    if os.environ.get("FLASK_DEBUG") or os.environ.get("FLASK_ENV") == "development":
        sys.exit(
            "Error: debug mode is not allowed in 'litfoundry serve'. "
            "Use development commands for development."
        )

    # Validate port
    if not isinstance(port, int) or port < 1 or port > 65535:
        sys.exit(f"Error: port must be between 1 and 65535, got {port}")

    # Loopback-only binding (always use 127.0.0.1, never configurable to non-loopback)
    bind_address = "127.0.0.1"

    # Create Flask app
    app = create_app()

    # Import Waitress
    try:
        from waitress import serve
    except ImportError:
        sys.exit("Error: waitress is required. Install with: pip install waitress")

    # Log server startup
    print(f"Starting LitFoundry server in {mode} mode on {bind_address}:{port}")
    print(f"Data root: {root}")
    if mode == "server":
        print("Use a reverse proxy (e.g., Caddy) for HTTPS and network access")
    else:
        print("Workstation mode: accessible only on localhost")

    # Run Waitress on loopback
    serve(app, host=bind_address, port=port, _quiet=True)
