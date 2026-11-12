# LitFoundry Project Lifecycle

## Overview

A LitFoundry project is a self-contained unit of work for systematic literature review. Each project has its own database, folder, and access control list (ACL). Projects go through defined lifecycle states from creation through deletion.

## Project States

Projects transition through the following states:

```
provisioning → ready ↔ archived → deleting → trash (purge)
                ↓                     ↓
            quarantined ←→ ready    error
```

### State Definitions

- **provisioning**: Temporary state during project creation. Project directory and database are being set up.
- **ready**: Normal operational state. Project is accessible to authorized users.
- **archived**: Read-only state. Project is archived for historical reference. No mutations allowed.
- **deleting**: Transitional state after deletion is initiated. Access is revoked, jobs are cancelled.
- **trash**: Project folder has been moved to `trash/` directory. Awaiting permanent purge.
- **quarantined**: Administrative quarantine. Project is inaccessible pending repair.
- **error**: Project database failed integrity check. Project is inaccessible until repaired.

## Storage Layout

Projects are stored in a hierarchical directory structure:

```
<data_root>/
  projects/
    <uuid-1>/
      project.sqlite         # Project database
      manifest.json          # Project metadata
      sources/               # Raw source data
      imports/               # Imported records
      attachments/           # Attached files
      figures/               # Generated figures
      reports/               # Generated reports
      exports/               # Exported data
      temp/                  # Temporary files
    <uuid-2>/
      ...
  trash/
    <uuid-3>/                # Deleted projects awaiting purge
    ...
  backup_staging/
    migrate-<timestamp>/     # Migration backups
```

## Lifecycle Transitions

### Provisioning → Ready

When a project is created:

1. An entry is inserted into `project_directory` with state `provisioning`
2. A staging folder `.staging-<uuid>` is created under `projects/`
3. The project database is created at the latest schema version
4. The manifest is written
5. All subdirectories are created
6. The staging folder is atomically renamed to the final location
7. The catalogue entry is updated to state `ready`

If any step fails, the staging folder and catalogue entry are cleaned up.

### Ready → Archived

When a project is archived:

1. The state is changed to `archived`
2. The updated_at timestamp is set
3. Any subsequent mutation attempts return 409 CONFLICT with detail `PROJECT_ARCHIVED`

### Archived ↔ Ready

Archived projects can be unarchived, returning to `ready` state.

### Ready/Archived → Deleting

When deletion is initiated (by owner or admin):

1. The state changes to `deleting`
2. Access is revoked (all requests get 409 PROJECT_UNAVAILABLE)
3. Background jobs are cancelled
4. A bounded wait (30 seconds by default) allows in-flight operations to complete
5. The project folder is moved from `projects/<uuid>` to `trash/<uuid>`
6. The catalogue state remains `deleting` temporarily

### Deleting → Deleted (Purge)

Housekeeping periodically purges trash:

1. For each project in `trash/`, check if retention period has elapsed
2. If elapsed, permanently delete the folder
3. Record the purge in audit events

### Ready → Quarantined

Administrators can quarantine a project:

1. The state changes to `quarantined`
2. Requests get 409 PROJECT_UNAVAILABLE

### Quarantined → Ready

After repair, administrators can release a quarantined project:

1. The state changes back to `ready`

### Any → Error

If a database integrity check fails at any time:

1. The state automatically changes to `error`
2. Requests get 409 PROJECT_UNAVAILABLE
3. An admin-visible alert is generated

## Database Schema Versions

Each project has a `project_schema_version` recorded in the catalogue. When `litfoundry migrate` runs:

1. It acquires the global maintenance lease
2. It backs up each project database
3. It runs Alembic migrations to bring each project to the latest version
4. It runs PRAGMA integrity_check to verify success
5. If a project fails, it is restored from backup and reported as failed
6. The catalogue records the new version for each project

Projects at non-current schema versions are unavailable (409 PROJECT_UNAVAILABLE).

## Access Control

Until `m2-project-access-control` is implemented:

- The project **owner** has full access (read, write, delete, transfer)
- **Admin** can access any project (read, write, admin actions like quarantine)
- **Other users** have no access by default

After ACL implementation, projects can be shared with specific users or made public with viewer or editor access levels.

## API Endpoints

### Project CRUD

- `POST /api/v1/projects` - Create project (owner-or-admin)
- `GET /api/v1/projects` - List accessible projects
- `GET /api/v1/projects/{project_id}` - Get project (viewer-or-admin)
- `PATCH /api/v1/projects/{project_id}` - Update project (owner-or-admin, If-Match)

### Lifecycle Actions

- `POST /api/v1/projects/{project_id}/archive` - Archive project (owner-or-admin)
- `POST /api/v1/projects/{project_id}/unarchive` - Unarchive project (owner-or-admin)
- `DELETE /api/v1/projects/{project_id}?confirm={title}` - Delete project (owner-or-admin)

### Ownership

- `POST /api/v1/projects/{project_id}/transfer-ownership` - Transfer ownership (owner-or-admin)
- `POST /api/v1/admin/users/{user_id}/transfer-projects` - Transfer all projects (admin)

### Admin Actions

- `POST /api/v1/admin/projects/{project_id}/quarantine` - Quarantine (admin)
- `POST /api/v1/admin/projects/{project_id}/release` - Release from quarantine (admin)

## Migration Procedure

To upgrade an installation:

1. Run `litfoundry migrate` to migrate all databases
2. The command acquires a maintenance lease for its duration
3. During migration, any new requests get 503 MAINTENANCE_IN_PROGRESS
4. After successful migration, the system is ready

## Reconciliation

`litfoundry reconcile` detects and repairs inconsistencies:

- Orphan `provisioning` rows (catalogue entry with no folder) → deleted
- Orphan folders (folder with no catalogue entry) → moved to trash
- Projects stuck in `deleting` (folder still exists) → moved to trash

Reconciliation is designed to run after crashes and recovers the system to a consistent state.
