"""Schema version gates for service startup and request processing."""

from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from werkzeug.exceptions import ServiceUnavailable, Conflict
from litfoundry.status import (
    get_catalogue_schema_version,
    get_expected_catalogue_schema_version,
    get_project_schema_versions,
)


class SchemaMismatchError(ServiceUnavailable):
    """Raised when schema version mismatch is detected."""
    
    def __init__(self, message: str):
        super().__init__(
            response={"detail": "SCHEMA_VERSION_MISMATCH", "error": message},
            code=503
        )


class ProjectUnavailableError(Conflict):
    """Raised when project cannot be accessed due to state or schema."""
    
    def __init__(self, detail: str, message: str = None):
        super().__init__(
            response={
                "detail": detail,
                "error": message or detail
            },
            code=409
        )


def check_catalogue_schema_on_startup(data_root: Path) -> None:
    """Check that catalogue schema is current before startup.
    
    Args:
        data_root: Path to data root directory
        
    Raises:
        SchemaMismatchError: If catalogue schema is out of sync
    """
    current = get_catalogue_schema_version(data_root)
    expected = get_expected_catalogue_schema_version()
    
    if current != expected:
        raise SchemaMismatchError(
            f"Catalogue schema v{current} does not match expected v{expected}. "
            f"Run 'litfoundry migrate' to upgrade."
        )


def check_project_schema_before_access(session: Session, project_id: str, data_root: Path) -> dict:
    """Check project schema version before allowing access.
    
    Args:
        session: Database session for catalogue
        project_id: UUID of project
        data_root: Path to data root
        
    Returns:
        Project record from catalogue
        
    Raises:
        ProjectUnavailableError: If project schema version or state is invalid
    """
    # Get project from catalogue
    result = session.execute(
        text("""
            SELECT id, owner_id, state, project_schema_version
            FROM project_directory
            WHERE id = :id
        """),
        {"id": project_id}
    ).first()
    
    if not result:
        raise ProjectUnavailableError(
            detail="PROJECT_NOT_FOUND",
            message=f"Project {project_id} does not exist"
        )
    
    project_id_val, owner_id, state, schema_version = result
    
    # Check state
    if state in ("deleting", "quarantined", "error"):
        raise ProjectUnavailableError(
            detail="PROJECT_UNAVAILABLE",
            message=f"Project is in {state} state"
        )
    
    # Check schema version
    expected = get_expected_catalogue_schema_version()
    if schema_version != expected:
        raise ProjectUnavailableError(
            detail="PROJECT_SCHEMA_MISMATCH",
            message=f"Project schema v{schema_version} does not match expected v{expected}"
        )
    
    # Verify project folder exists
    project_folder = data_root / "projects" / project_id_val
    if not project_folder.exists():
        raise ProjectUnavailableError(
            detail="PROJECT_UNAVAILABLE",
            message=f"Project folder does not exist"
        )
    
    return {
        "id": project_id_val,
        "owner_id": owner_id,
        "state": state,
        "schema_version": schema_version
    }


def check_archived_state(session: Session, project_id: str) -> None:
    """Check that project is not archived before mutation.
    
    Args:
        session: Database session for catalogue
        project_id: UUID of project
        
    Raises:
        ProjectUnavailableError: If project is archived
    """
    result = session.execute(
        text("SELECT state FROM project_directory WHERE id = :id"),
        {"id": project_id}
    ).first()
    
    if result and result[0] == "archived":
        raise ProjectUnavailableError(
            detail="PROJECT_ARCHIVED",
            message="Project is archived and cannot be modified"
        )
