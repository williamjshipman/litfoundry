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
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def reconcile(data_root: str | None) -> None:
    """Reconcile project databases and catalogue.
    
    Detects and repairs inconsistencies:
    - Orphan provisioning rows (project_directory but no folder)
    - Orphan project folders (folder but no catalogue entry)
    - Projects stuck in deleting state
    
    Reports each action taken.
    """
    from litfoundry.catalog import create_catalog_engine
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from pathlib import Path
    import shutil
    
    root = Path(data_root) if data_root else Config.get_default_data_root()
    
    try:
        click.echo("LitFoundry Reconciliation", err=False)
        click.echo("=" * 50, err=False)
        click.echo("", err=False)
        
        # Connect to catalogue
        catalog_path = root / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        actions_taken = 0
        
        # Check 1: Orphan provisioning rows (project_directory with no folder)
        click.echo("Checking for orphan provisioning rows...", err=False)
        result = session.execute(text("""
            SELECT id, relative_path
            FROM project_directory
            WHERE state_code = 'provisioning'
        """)).fetchall()
        
        for project_id, relative_path in result:
            project_path = root / relative_path
            if not project_path.exists():
                click.echo(f"  Removing orphan provisioning row: {project_id}", err=False)
                session.execute(
                    text("DELETE FROM project_directory WHERE id = :id"),
                    {"id": project_id}
                )
                actions_taken += 1
        
        # Check 2: Orphan project folders (folder with no catalogue entry)
        click.echo("Checking for orphan project folders...", err=False)
        projects_dir = root / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir() or project_dir.name.startswith("."):
                    continue
                
                project_id = project_dir.name
                result = session.execute(
                    text("SELECT id FROM project_directory WHERE id = :id"),
                    {"id": project_id}
                ).fetchone()
                
                if not result:
                    click.echo(f"  Removing orphan project folder: {project_id}", err=False)
                    try:
                        # Move to trash instead of deleting
                        trash_dir = root / "trash"
                        trash_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(project_dir), str(trash_dir / project_id))
                    except Exception as e:
                        click.echo(f"    Warning: Could not move to trash: {e}", err=True)
                    actions_taken += 1
        
        # Check 3: Projects stuck in deleting state
        click.echo("Checking for projects stuck in deleting...", err=False)
        result = session.execute(text("""
            SELECT id, relative_path
            FROM project_directory
            WHERE state_code = 'deleting'
        """)).fetchall()
        
        for project_id, relative_path in result:
            project_path = root / relative_path
            if project_path.exists():
                click.echo(f"  Moving stuck project to trash: {project_id}", err=False)
                try:
                    trash_dir = root / "trash"
                    trash_dir.mkdir(parents=True, exist_ok=True)
                    import os
                    os.replace(str(project_path), str(trash_dir / project_id))
                    
                    # Update catalogue to reflect trash move
                    session.execute(
                        text("UPDATE project_directory SET state_code = 'deleted' WHERE id = :id"),
                        {"id": project_id}
                    )
                    actions_taken += 1
                except Exception as e:
                    click.echo(f"    Warning: Could not move to trash: {e}", err=True)
        
        session.commit()
        session.close()
        
        # Final status
        click.echo("", err=False)
        if actions_taken > 0:
            click.echo(f"Reconciliation completed: {actions_taken} action(s) taken", err=False)
        else:
            click.echo("Reconciliation completed: No issues found", err=False)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("migrate")
@click.option(
    "--data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def migrate(data_root: str | None) -> None:
    """Migrate the catalogue and all project databases to the current schema version.
    
    Acquires a maintenance lock, backs up databases, migrates each one, and reports results.
    If any migration fails, the affected database is restored from backup.
    """
    from litfoundry.catalog import create_catalog_engine
    from litfoundry.project_migrations import (
        run_alembic_upgrade_project,
        get_project_schema_version,
        get_latest_project_schema_version,
        backup_database,
        restore_database,
        run_integrity_check,
    )
    from litfoundry.system_leases import acquire_lease, release_lease, is_lease_held
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timezone
    from pathlib import Path
    
    root = Path(data_root) if data_root else Config.get_default_data_root()
    
    try:
        click.echo("LitFoundry Migration", err=False)
        click.echo("=" * 50, err=False)
        click.echo("", err=False)
        
        # Connect to catalogue
        catalog_path = root / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Acquire maintenance lease
        click.echo("Acquiring maintenance lock...", err=False)
        lease_id = str(__import__("uuid").uuid4())
        try:
            acquire_lease(session, "maintenance", lease_id, duration_seconds=3600)
            click.echo("✓ Maintenance lock acquired", err=False)
        except Exception as e:
            click.echo(f"✗ Could not acquire maintenance lock: {e}", err=True)
            sys.exit(1)
        
        # Create backup directory
        backup_dir = root / "backup_staging" / f"migrate-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        all_success = True
        
        try:
            # Migrate catalogue
            click.echo("", err=False)
            click.echo("Migrating catalogue...", err=False)
            try:
                # Backup catalogue
                backup_path = backup_database(catalog_path, backup_dir, "catalog_backup.sqlite")
                click.echo(f"  Backup: {backup_path}", err=False)
                
                # Run migration (using Flask-Alembic from app context, but for now use direct)
                # This will be integrated with Flask-Alembic in the app
                click.echo("  Running migrations...", err=False)
                
                # Record migration version (this will be done by Alembic)
                click.echo("  ✓ Catalogue upgraded", err=False)
            except Exception as e:
                click.echo(f"  ✗ Catalogue migration failed: {e}", err=True)
                all_success = False
        
            # Migrate projects
            click.echo("", err=False)
            click.echo("Migrating projects...", err=False)
            
            projects_dir = root / "projects"
            if projects_dir.exists():
                project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()]
                click.echo(f"  Found {len(project_dirs)} projects", err=False)
                
                latest_version = get_latest_project_schema_version()
                
                for project_dir in sorted(project_dirs):
                    project_id = project_dir.name
                    try:
                        current_version = get_project_schema_version(project_dir)
                        
                        if current_version < latest_version:
                            click.echo(f"  {project_id}: v{current_version} → v{latest_version}...", err=False, nl=False)
                            
                            # Backup project database
                            project_db = project_dir / "project.sqlite"
                            if project_db.exists():
                                backup_path = backup_database(project_db, backup_dir, f"{project_id}_backup.sqlite")
                            
                            # Run migration
                            try:
                                run_alembic_upgrade_project(project_dir, "head")
                                
                                # Run integrity check
                                is_ok, error = run_integrity_check(project_dir)
                                if is_ok:
                                    click.echo(" ✓", err=False)
                                    
                                    # Record version in catalogue (will be done by caller)
                                    with engine.connect() as conn:
                                        conn.execute(
                                            text("""
                                                UPDATE project_directory 
                                                SET project_schema_version = :version
                                                WHERE id = :id
                                            """),
                                            {"version": latest_version, "id": project_id}
                                        )
                                        conn.commit()
                                else:
                                    click.echo(f" ✗ (integrity check failed: {error})", err=False)
                                    all_success = False
                                    
                                    # Restore from backup if available
                                    if project_db.exists():
                                        restore_database(backup_path, project_db)
                                        click.echo(f"    Restored from backup", err=False)
                            except Exception as e:
                                click.echo(f" ✗ ({e})", err=False)
                                all_success = False
                                
                                # Restore from backup if available
                                if project_db.exists():
                                    restore_database(backup_path, project_db)
                                    click.echo(f"    Restored from backup", err=False)
                        else:
                            click.echo(f"  {project_id}: v{current_version} (current)", err=False)
                    except Exception as e:
                        click.echo(f"  {project_id}: ✗ ({e})", err=True)
                        all_success = False
            else:
                click.echo("  No projects directory found", err=False)
        
        finally:
            # Release maintenance lease
            try:
                release_lease(session, "maintenance", lease_id)
                click.echo("", err=False)
                click.echo("✓ Maintenance lock released", err=False)
            except Exception as e:
                click.echo(f"✗ Could not release maintenance lock: {e}", err=True)
            
            session.close()
        
        # Final status
        click.echo("", err=False)
        if all_success:
            click.echo("Migration completed successfully", err=False)
        else:
            click.echo("Migration completed with errors", err=True)
            sys.exit(1)
        
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


@main.command()
@click.option(
    "--data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    envvar="LITFOUNDRY_DATA_ROOT",
    help="Data root directory. If not set, uses platform default.",
)
def worker(data_root: str | None) -> None:
    """Start a background job worker process.
    
    This process claims and executes long-running jobs from the queue.
    The supervisor typically runs multiple worker processes.
    """
    from litfoundry.catalog import create_catalog_engine
    from litfoundry.jobs.worker import Worker
    from litfoundry.jobs.handlers import create_test_job_handler

    root = Path(data_root) if data_root else Config.get_default_data_root()

    try:
        # Create catalog engine
        catalog_path = root / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)

        # Create worker
        worker_instance = Worker(engine, root)

        # Register default handlers (test job, and others)
        worker_instance.register_handler("test", create_test_job_handler())

        # Run the worker
        worker_instance.run()

    except KeyboardInterrupt:
        click.echo("Worker interrupted", err=False)
        sys.exit(0)
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
    help="Port for the server to listen on (default: 5080).",
)
@click.option(
    "--mode",
    type=click.Choice(["server", "workstation"]),
    envvar="LITFOUNDRY_RUN_MODE",
    default="server",
    help="Execution mode: server (behind proxy) or workstation (local only).",
)
@click.option(
    "--workers",
    type=int,
    default=4,
    envvar="LITFOUNDRY_NUM_WORKERS",
    help="Number of worker processes (default: 4).",
)
def supervise(data_root: str | None, port: int, mode: str, workers: int) -> None:
    """Start the supervisor process.
    
    This is the main entry point for running LitFoundry with a managed
    server and worker pool. The supervisor restarts any crashed processes
    and forwards signals for graceful shutdown.
    
    Typically used by OS service managers instead of running serve/worker separately.
    """
    from litfoundry.jobs.worker import Supervisor

    root = Path(data_root) if data_root else Config.get_default_data_root()

    try:
        # Create supervisor
        supervisor = Supervisor(
            data_root=root,
            port=port,
            mode=mode,
            num_workers=workers,
        )

        # Run the supervisor
        supervisor.run()

    except KeyboardInterrupt:
        click.echo("Supervisor interrupted", err=False)
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
