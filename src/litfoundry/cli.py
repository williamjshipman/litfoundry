"""LitFoundry command-line interface."""

import sys
from pathlib import Path

import click

from litfoundry import __version__
from litfoundry.config import Config


@click.group()
@click.version_option(version=__version__, prog_name="litfoundry")
def main() -> None:
    """LitFoundry: systematic literature reviews and bibliometric analysis."""
    pass


@main.command()
@click.option(
    "--data-root",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def init(data_root: str | None) -> None:
    """Initialize a new LitFoundry data root."""
    from litfoundry.initialization import initialize_data_root

    root = Path(data_root) if data_root else Config.get_default_data_root()

    try:
        initialize_data_root(root)
        click.echo(f"Initialized LitFoundry data root at: {root}", err=False)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
@click.option(
    "--port",
    type=int,
    default=5080,
    envvar="LITFOUNDRY_PORT",
    help="Port to listen on (default: 5080).",
)
@click.option(
    "--mode",
    type=click.Choice(["server", "workstation"]),
    default="server",
    envvar="LITFOUNDRY_RUN_MODE",
    help="Execution mode: server (behind proxy) or workstation (local only).",
)
def serve(data_root: str | None, port: int, mode: str) -> None:
    """Start the LitFoundry server."""
    from litfoundry.server import start_server

    root = Path(data_root) if data_root else Config.get_default_data_root()

    try:
        start_server(root, port=port, mode=mode)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    "--data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def status(data_root: str | None) -> None:
    """Check the status of a LitFoundry installation.
    
    Displays health checks and exits non-zero if any critical checks fail.
    """
    from litfoundry.status import check_status

    root = Path(data_root) if data_root else Config.get_default_data_root()

    try:
        result = check_status(root)
        
        # Print header with overall status
        status_str = result["status"].upper()
        click.echo(f"LitFoundry Status: {status_str}", err=False)
        click.echo(f"Version: {result['version']}", err=False)
        click.echo("", err=False)
        
        # Print individual checks
        click.echo("Health Checks:", err=False)
        for check_name, check_result in result["checks"].items():
            status_val = check_result.get("status", "unknown").upper()
            reason = check_result.get("reason", "")
            path = check_result.get("path", "")
            free_mb = check_result.get("free_mb", "")
            
            # Format output for each check
            line = f"  {check_name}: {status_val}"
            if reason:
                line += f" ({reason})"
            elif path:
                line += f" ({path})"
            elif free_mb:
                line += f" ({free_mb} MB)"
            
            click.echo(line, err=False)
        
        # Exit non-zero if not healthy
        if not result["healthy"]:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
