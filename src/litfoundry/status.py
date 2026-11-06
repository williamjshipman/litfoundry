"""System status checking for LitFoundry."""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from litfoundry import __version__


def check_status(data_root: Path) -> dict[str, Any]:
    """Check the status of a LitFoundry installation.
    
    Returns a dictionary with:
    - status: overall status string ("healthy", "degraded", "broken")
    - healthy: boolean indicating if all critical checks passed
    - version: application version
    - checks: dict of individual check results
    
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
    try:
        catalogue_db = data_root / "catalog.sqlite"
        if not catalogue_db.is_file():
            checks["catalogue"] = {
                "status": "failed",
                "reason": "Catalogue database not found"
            }
            all_healthy = False
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
                    else:
                        conn.close()
                        checks["catalogue"] = {"status": "ok"}
            except Exception as e:
                checks["catalogue"] = {
                    "status": "failed",
                    "reason": f"Catalogue database error: {str(e)}"
                }
                all_healthy = False
    except Exception as e:
        checks["catalogue"] = {
            "status": "failed",
            "reason": str(e)
        }
        all_healthy = False
    
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
    
    # Determine overall status
    if all_healthy:
        status = "healthy"
    else:
        status = "broken"
    
    return {
        "status": status,
        "healthy": all_healthy,
        "version": __version__,
        "checks": checks
    }

