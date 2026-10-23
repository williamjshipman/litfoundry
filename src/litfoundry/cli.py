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
    """Check the status of a LitFoundry installation."""
    from litfoundry.status import check_status

    root = Path(data_root) if data_root else Config.get_default_data_root()

    try:
        result = check_status(root)
        click.echo(f"Status: {result['status']}", err=False)
        if not result["healthy"]:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
