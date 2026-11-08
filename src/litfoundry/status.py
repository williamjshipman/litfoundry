"""System status checking for LitFoundry."""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from litfoundry import __version__


def get_catalogue_schema_version(catalogue_db: Path) -> int:
    """Get the current schema version of the catalogue database.
    
    Args:
        catalogue_db: Path to the catalogue database
        
    Returns:
        Schema version number, or 0 if not found
    """
    try:
        conn = sqlite3.connect(str(catalogue_db))
        cursor = conn.cursor()
        
        # Get the latest version from alembic_version table
        cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return 0
        
        # Extract version number from revision ID
        version_str = row[0].split("_")[0]
        return int(version_str)
    except Exception:
        return 0


def get_expected_catalogue_schema_version() -> int:
    """Get the expected (latest) catalogue schema version.
    
    Returns:
        The latest schema version number
    """
    project_root = Path(__file__).parent.parent.parent  # Up from src/litfoundry/
    versions_dir = project_root / "migrations" / "catalog" / "versions"
    
    if not versions_dir.exists():
        return 0
    
    # Find the highest numbered migration file
    max_version = 0
    for f in versions_dir.glob("*.py"):
        if f.name == "__init__.py" or f.name == "__pycache__":
            continue
        try:
            version = int(f.name.split("_")[0])
            max_version = max(max_version, version)
        except (ValueError, IndexError):
            pass
    
    return max_version


def get_project_schema_versions(data_root: Path) -> dict[str, int]:
    """Get schema versions for all projects.
    
    Args:
        data_root: Path to the data root
        
    Returns:
        Dict mapping project ID to schema version
    """
    versions = {}
    
    projects_dir = data_root / "projects"
    if not projects_dir.exists():
        return versions
    
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        
        project_id = project_dir.name
        project_db = project_dir / "project.sqlite"
        
        if not project_db.exists():
            versions[project_id] = 0
            continue
        
        try:
            conn = sqlite3.connect(str(project_db))
            cursor = conn.cursor()
            
            cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            if row:
                version_str = row[0].split("_")[0]
                versions[project_id] = int(version_str)
            else:
                versions[project_id] = 0
        except Exception:
            versions[project_id] = 0
    
    return versions


def check_status(data_root: Path) -> dict[str, Any]:
    """Check the status of a LitFoundry installation.
    
    Returns a dictionary with:
    - status: overall status string ("healthy", "degraded", "broken")
    - healthy: boolean indicating if all critical checks passed
    - version: application version
    - checks: dict of individual check results
    - migrations: migration status info
    
    Exits with non-zero status if any critical check fails.
    """
    checks = {}
    all_healthy = True
    
    # Check 1: Data root exists and is accessible
    try:
        if not data_root.is_dir():
            checks["data_root"] = {
                "status": "failed",
                "reason": "Data root directory not found"
            }
            all_healthy = False
        else:
            checks["data_root"] = {
                "status": "ok",
                "path": str(data_root)
            }
    except Exception as e:
        checks["data_root"] = {
            "status": "failed",
            "reason": str(e)
        }
        all_healthy = False
    
    # Check 2: Initialization marker exists
    try:
        initialized_marker = data_root / ".initialized"
        if initialized_marker.exists():
            checks["initialization"] = {"status": "ok"}
        else:
            checks["initialization"] = {
                "status": "failed",
                "reason": "Data root not initialized (missing .initialized marker)"
            }
            all_healthy = False
    except Exception as e:
        checks["initialization"] = {
            "status": "failed",
            "reason": str(e)
        }
        all_healthy = False
    
    # Check 3: Catalogue database exists and is readable
    catalogue_schema_ok = True
    try:
        catalogue_db = data_root / "catalog.sqlite"
        if not catalogue_db.is_file():
            checks["catalogue"] = {
                "status": "failed",
                "reason": "Catalogue database not found"
            }
            all_healthy = False
            catalogue_schema_ok = False
        else:
            # Try to connect and verify schema is initialized
            try:
                conn = sqlite3.connect(f"file:{catalogue_db}?mode=ro", uri=True, timeout=1)
                cursor = conn.cursor()
                
                # Check that required schema tables exist
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
                )
                if not cursor.fetchone():
                    conn.close()
                    checks["catalogue"] = {
                        "status": "failed",
                        "reason": "Catalogue schema not initialized (missing schema_meta table)"
                    }
                    all_healthy = False
                    catalogue_schema_ok = False
                else:
                    # Check system_settings table as well
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'"
                    )
                    if not cursor.fetchone():
                        conn.close()
                        checks["catalogue"] = {
                            "status": "failed",
                            "reason": "Catalogue schema incomplete (missing system_settings table)"
                        }
                        all_healthy = False
                        catalogue_schema_ok = False
                    else:
                        conn.close()
                        checks["catalogue"] = {"status": "ok"}
            except Exception as e:
                checks["catalogue"] = {
                    "status": "failed",
                    "reason": f"Catalogue database error: {str(e)}"
                }
                all_healthy = False
                catalogue_schema_ok = False
    except Exception as e:
        checks["catalogue"] = {
            "status": "failed",
            "reason": str(e)
        }
        all_healthy = False
        catalogue_schema_ok = False
    
    # Check 4: Logs directory exists
    try:
        logs_dir = data_root / "logs"
        if logs_dir.exists():
            checks["logs"] = {"status": "ok"}
        else:
            checks["logs"] = {
                "status": "warning",
                "reason": "Logs directory not found (will be created on first run)"
            }
    except Exception as e:
        checks["logs"] = {
            "status": "warning",
            "reason": str(e)
        }
    
    # Check 5: Disk space
    try:
        stat_result = shutil.disk_usage(data_root)
        free_mb = stat_result.free / (1024 * 1024)
        
        if free_mb < 100:
            checks["disk_space"] = {
                "status": "failed",
                "reason": f"Low disk space: {free_mb:.1f} MB free (minimum 100 MB required)"
            }
            all_healthy = False
        elif free_mb < 500:
            checks["disk_space"] = {
                "status": "warning",
                "reason": f"Low disk space: {free_mb:.1f} MB free"
            }
        else:
            checks["disk_space"] = {
                "status": "ok",
                "free_mb": f"{free_mb:.1f}"
            }
    except Exception as e:
        checks["disk_space"] = {
            "status": "warning",
            "reason": str(e)
        }
    
    # Check 6: Job queue health (if catalyst connected)
    try:
        from litfoundry.catalog import create_catalog_engine
        from litfoundry.jobs.queue import JobQueue
        
        catalogue_db = data_root / "catalog.sqlite"
        if catalogue_db.is_file():
            engine = create_catalog_engine(catalogue_db)
            queue = JobQueue(engine)
            health = queue.get_queue_health()
            
            # Check if we have workers
            active_workers = [w for w in health.get("worker_heartbeats", []) if w["status"] == "active"]
            running_count = health.get("running_count", 0)
            
            if running_count > 0 and len(active_workers) == 0:
                checks["job_queue"] = {
                    "status": "warning",
                    "reason": "Jobs running but no active workers (stale leases)"
                }
            else:
                checks["job_queue"] = {
                    "status": "ok",
                    "queued": health.get("queued_count", 0),
                    "running": running_count,
                    "workers": len(active_workers)
                }
    except Exception as e:
        checks["job_queue"] = {
            "status": "warning",
            "reason": f"Could not check job queue: {e}"
        }
    
    # Check 7: Migration status
    migrations = {}
    if catalogue_schema_ok:
        try:
            current_version = get_catalogue_schema_version(data_root / "catalog.sqlite")
            expected_version = get_expected_catalogue_schema_version()
            
            if current_version < expected_version:
                checks["migrations"] = {
                    "status": "warning",
                    "reason": f"Catalogue schema v{current_version}, expected v{expected_version}. Run 'litfoundry migrate'"
                }
                migrations["status"] = "pending"
                migrations["catalogue_current"] = current_version
                migrations["catalogue_expected"] = expected_version
            else:
                checks["migrations"] = {"status": "ok"}
                migrations["status"] = "current"
                migrations["catalogue_version"] = current_version
            
            # Check project schema versions
            project_versions = get_project_schema_versions(data_root)
            expected_project_version = 1  # Latest project schema version
            
            at_current = 0
            pending = 0
            for project_id, version in sorted(project_versions.items()):
                if version < expected_project_version:
                    pending += 1
                else:
                    at_current += 1
            
            if pending > 0:
                migrations["projects_pending_migration"] = pending
                migrations["projects_current"] = at_current
            else:
                migrations["projects_current"] = at_current
        except Exception as e:
            checks["migrations"] = {
                "status": "warning",
                "reason": f"Could not check migration status: {e}"
            }
    
    # Determine overall status
    if all_healthy:
        status = "healthy"
    else:
        status = "broken"
    
    return {
        "status": status,
        "healthy": all_healthy,
        "version": __version__,
        "checks": checks,
        "migrations": migrations
    }

