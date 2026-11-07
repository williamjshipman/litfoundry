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
    envvar="LITFOUNDRY_RUN_MODE",
    required=True,
    help="Execution mode: server (behind proxy) or workstation (local only). Required.",
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


@main.group()
def admin() -> None:
    """Administration commands (host-only access required)."""
    pass


@admin.command("reset-password")
@click.option(
    "--data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def admin_reset_password(data_root: str | None) -> None:
    """Reset the admin account password (host-only recovery).
    
    This command requires operating system access to the data root and is
    not accessible through the web API. It revokes all admin sessions and
    records an audit event.
    """
    from litfoundry.catalog import create_catalog_engine, User, AuditEvent
    from litfoundry.auth import LocalProvider
    from pathlib import Path
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timezone
    from uuid import uuid4
    
    root = Path(data_root) if data_root else Config.get_default_data_root()
    
    try:
        # Connect to catalog
        catalog_path = root / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Find admin user
        admin = session.query(User).filter_by(role="admin").first()
        if not admin:
            click.echo("Error: No admin account found", err=True)
            sys.exit(1)
        
        # Prompt for new password
        while True:
            password = click.prompt("New admin password", hide_input=True, confirmation_prompt=True)
            if len(password) < 8:
                click.echo("Error: Password must be at least 8 characters", err=True)
                continue
            break
        
        # Reset password
        provider = LocalProvider()
        provider.change_password(admin, password, session)
        
        # Increment session_version to revoke all sessions
        admin.session_version += 1
        
        # Record audit event
        audit = AuditEvent(
            id=str(uuid4()),
            actor_user_id=None,  # Host action, no user
            action="admin_password_reset",
            resource_type="user",
            resource_id=admin.id,
            status="success",
            created_at=datetime.now(timezone.utc),
        )
        session.add(audit)
        
        session.commit()
        session.close()
        
        click.echo("Admin password reset successfully", err=False)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("bootstrap-token")
@click.option(
    "--data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def bootstrap_token(data_root: str | None) -> None:
    """Issue a new bootstrap token for setup (while setup is pending).
    
    Generates a new single-use token valid for 30 minutes.
    Only works when no admin account exists yet.
    """
    from litfoundry.catalog import create_catalog_engine, User, BootstrapToken
    from litfoundry.auth.bootstrap import (
        generate_bootstrap_token,
        hash_bootstrap_token,
        write_bootstrap_token_file,
        get_bootstrap_token_expiry_time,
    )
    from pathlib import Path
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timezone
    from uuid import uuid4
    
    root = Path(data_root) if data_root else Config.get_default_data_root()
    
    try:
        # Connect to catalog
        catalog_path = root / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if admin exists (setup complete)
        admin = session.query(User).filter_by(role="admin").first()
        if admin:
            click.echo("Error: Setup is already complete", err=True)
            sys.exit(1)
        
        # Generate new token
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        now = datetime.now(timezone.utc)
        expires_at = get_bootstrap_token_expiry_time(now)
        
        # Delete any old unconsumed tokens
        session.query(BootstrapToken).filter_by(consumed_at=None).delete()
        
        # Store new token hash in database
        boot_token = BootstrapToken(
            token_hash=token_hash,
            expires_at=expires_at,
            consumed_at=None,
        )
        session.add(boot_token)
        session.commit()
        
        # Write token file
        try:
            write_bootstrap_token_file(root, token)
            click.echo(f"Bootstrap token written to {root / 'bootstrap-token.txt'}", err=False)
        except Exception as e:
            click.echo(f"Warning: Could not write token file: {e}", err=True)
        
        # Display token (only on first generation; warn about file write)
        click.echo("", err=False)
        click.echo("Bootstrap Token (valid for 30 minutes):", err=False)
        click.echo(token, err=False)
        click.echo("", err=False)
        click.echo("Use this token with: POST /api/v1/setup/admin", err=False)
        
        session.close()
        
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
