"""Server startup and management."""

import logging
import os
import sys
from pathlib import Path

from litfoundry.app import create_app
from litfoundry.config import Config
from litfoundry.logging import setup_logging


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

    # Set up structured logging
    setup_logging(
        root,
        process_name="litfoundry-server",
        level=logging.INFO,
    )

    # Log that server is starting
    logger = logging.getLogger(__name__)
    logger.info(f"Starting LitFoundry server initialization for {root}")

    # Check if data root is initialized; warn if not
    initialized_marker = root / ".initialized"
    if not initialized_marker.exists():
        print(
            f"Warning: Data root at {root} does not appear to be initialized.",
            file=sys.stderr,
        )
        print("Run 'litfoundry init --data-root <root>' first.", file=sys.stderr)

    # Note: mode is guaranteed to be valid ('server' or 'workstation') by Click's choice validator

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

    # Load environment configuration and merge with data root and mode
    env_config = Config.load_from_env()
    app_config = env_config.to_dict()

    # Override with runtime arguments (data root and mode are always explicit)
    app_config["LITFOUNDRY_DATA_ROOT"] = str(root)
    app_config["LITFOUNDRY_RUN_MODE"] = mode
    app_config["LITFOUNDRY_PORT"] = port

    # Create Flask app with full configuration
    app = create_app(app_config)

    # Import Waitress
    try:
        from waitress import serve
    except ImportError:
        sys.exit("Error: waitress is required. Install with: pip install waitress")

    # Log server startup with configured settings
    print(f"Starting LitFoundry server in {mode} mode on {bind_address}:{port}")
    print(f"Data root: {root}")

    # Show configured middleware settings
    if app_config.get("LITFOUNDRY_TRUSTED_PROXIES"):
        print(f"Trusted proxies: {app_config['LITFOUNDRY_TRUSTED_PROXIES']}")
    if app_config.get("LITFOUNDRY_ALLOWED_HOSTS"):
        print(f"Allowed hosts: {app_config['LITFOUNDRY_ALLOWED_HOSTS']}")
    if app_config.get("LITFOUNDRY_CORS_ORIGINS"):
        print(f"CORS origins: {app_config['LITFOUNDRY_CORS_ORIGINS']}")

    if mode == "server":
        print("Use a reverse proxy (e.g., Caddy) for HTTPS and network access")
    else:
        print("Workstation mode: accessible only on localhost")

    # Configure Waitress with trusted proxy settings
    # Parse trusted proxies from config for Waitress
    waitress_kwargs = {}
    trusted_proxies_str = app_config.get("LITFOUNDRY_TRUSTED_PROXIES", "")
    if trusted_proxies_str:
        trusted_proxy_list = [ip.strip() for ip in trusted_proxies_str.split(",") if ip.strip()]
        if trusted_proxy_list:
            # Waitress accepts trusted_proxy as list of IP addresses
            # or '*' to trust all proxies (NOT recommended)
            waitress_kwargs["trusted_proxy"] = trusted_proxy_list

    # Run Waitress on loopback with optional trusted proxy settings
    serve(app, host=bind_address, port=port, _quiet=True, **waitress_kwargs)
