# Design: M2 project workspaces

## Context

The catalogue, identity and API contract exist (M1). This change introduces the second database type, `project.sqlite`, of which there is one per project and an open-ended number in total. It also introduces the routing that makes each request touch only one project.

## Goals / Non-Goals

**Goals:**
- Project database routing that scales to hundreds of projects without registering fixed Flask binds.
- Lifecycle states that survive crashes and can be reconciled.

**Non-Goals:**
- Sharing, ACLs and the full access-resolution order (`m2-project-access-control`). Until that lands, access is owner plus admin.
- Job cancellation on delete (`m2-background-jobs`).
- Project export and import (`m7-project-export-import`).

## Decisions

### Engine routing
- **Resolution:** `ProjectDatabaseRouter.open(project_uuid)` resolves the folder through `project_directory.relative_path` and checks containment. It re-reads `project_directory.state` and `project_schema_version` before opening, then returns a short-lived SQLAlchemy `Session`.
- **Pooling:** engines use `NullPool` and apply PRAGMAs (WAL, `foreign_keys=ON`, `busy_timeout`) on each connect, so no handles stay open between operations. An LRU cache may keep engine objects, which hold no connections under `NullPool`.
- **Alternative rejected:** Flask-SQLAlchemy binds per project. They are fixed at startup and keep pooled connections open, which blocks Windows folder renames (v1.3 §4.3.2).

### Provisioning
1. Insert a `project_directory` row with state `provisioning` and `relative_path=projects/<uuid>`.
2. Create `projects/.staging-<uuid>/`, then the database at head through Alembic, the subdirectories and `manifest.json`.
3. Call `os.replace` to the final name on the same filesystem.
4. Set the state to `ready`.

On failure, remove the staging folder and delete the row in a `finally` path. `reconcile` handles crashes in between.

### Migrations
- **Catalogue:** Flask-Alembic (`migrations/catalog/`).
- **Projects:** plain Alembic (`migrations/project/`), driven programmatically. `command.upgrade(cfg, "head")` runs with `cfg.attributes["connection"]` set to a connection on that project's engine, following the Alembic cookbook pattern for sharing a connection.
- **Why not Flask-Alembic for projects:** its documentation does not cover an open-ended set of database files (v1.3 A.3).
- **Order of work:** `litfoundry migrate` acquires the `maintenance` system lease (fenced), backs up each database with `sqlite3.Connection.backup()` into `backup_staging/migrate-<run>/`, migrates the catalogue first and then each project sequentially. After each project it runs `PRAGMA integrity_check` and records the result.
- **Failure:** a failing project is restored from its copy with the backup API.
- **Lease timing:** the `system_leases` table and the maintenance lease are created here. `m2-background-jobs` reuses them for the write barrier.

### State machine
| From | To | Trigger |
|---|---|---|
| `provisioning` | `ready` | Provisioning completes |
| `ready` | `archived` | Archive |
| `archived` | `ready` | Unarchive |
| `ready` or `archived` | `deleting` | Delete |
| `deleting` | trash folder, then purge | Deletion proceeds |
| `ready` | `quarantined` | Admin quarantines |
| `quarantined` | `ready` | Admin releases |
| any | `error` | Integrity failure is detected |

- **Leaving `error`:** an `error` project returns to `ready` only through quarantine and release after repair.
- **Purge timing:** housekeeping skips trash purges while the `full-backup` lease is held (enforced in M7).

### Deletion confirmation
`DELETE` requires `?confirm=<project title>`. The GUI's confirmation dialog supplies it.

### Error code additions
`PROJECT_UNAVAILABLE` (409) is added, and `PROJECT_ARCHIVED` is a `CONFLICT` detail. Both are recorded in `docs/decisions.md`.

## Risks / Trade-offs

- [Many projects make `migrate` slow] → It runs sequentially by design (v1.3), reports progress per project and can be resumed because versions are recorded per project.
- [`NullPool` reconnect overhead] → SQLite connection setup is cheap. PRAGMAs are applied on each connect, so behaviour stays consistent.
- [A crash between the catalogue write and the folder rename] → Workflow states plus `reconcile` cover this, with tests that kill the process at each step.

## Migration Plan

This change adds catalogue revisions for `project_directory` and `system_leases`, and the first project-template revision (`project_info`, `project_audit_events`, `project_people`). There is no earlier data.
