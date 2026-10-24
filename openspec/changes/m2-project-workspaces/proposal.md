# Proposal: M2 project workspaces

## Why

LitFoundry's central design decision is that each project is a physically separate folder with its own `project.sqlite`, while a central catalogue records ownership, discovery and state (v1.3 decision 3). Every research feature from M3 onward stores its data in a project, so project creation, isolation, lifecycle and schema migration must exist first.

## What Changes

- **Provisioning:** projects are created through a staging folder and an atomic rename, with failure clean-up. The catalogue states are `provisioning`, `ready`, `archived`, `quarantined`, `deleting` and `error`.
- **Project API:** list, view, update, archive and unarchive. Deletion is two-stage, through `trash/`, with a purge.
- **Ownership transfer:** per project, and in bulk for all of a user's projects (admin).
- **Quarantine:** the admin can quarantine and release damaged projects.
- **Per-project storage:**
  - each project lives in its own UUID-named folder;
  - ownership is recorded only in the catalogue;
  - write-once project files;
  - database handles are released between operations (needed on Windows);
  - `litfoundry reconcile` repairs cross-database workflow states.
- **Schema migrations:** catalogue and project-template migrations, run by `litfoundry migrate` under a maintenance lock with a pre-migration backup. Schema versions are recorded, and the server refuses to run against mismatched schemas.
- **GUI:**
  - the Home page lists owned, shared and visible projects;
  - the new-project wizard's project-details step;
  - the project workspace frame and its Overview tab.

## Capabilities

### New Capabilities

- `projects/project-lifecycle`: creating, listing, viewing, updating, archiving, deleting, transferring and quarantining projects.
- `projects/project-storage`: per-project folders and databases, isolation, write-once files, handle release and reconciliation.
- `platform/schema-migrations`: versioned catalogue and project schemas, the `litfoundry migrate` command, version gating and failure recovery.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §1: decision 3 and the project rights for delete/archive;
  - §4: the data layout under `projects/`;
  - §4.1: the `project_directory` table;
  - §4.2: the `project_info` and `project_audit_events` tables;
  - §4.3;
  - §13: Home, the new-project wizard and the workspace frame;
  - §14: the `/projects`, archive, transfer and admin transfer-projects routes;
  - §18.1: `migrate` and `reconcile`;
  - §19: groups 3 and 4;
  - §20: M2.
- **Depends on:** `m1-platform-foundation`, `m1-web-foundation` and `m1-local-identity`.
- **Followed by:** `m2-project-access-control`, which adds sharing and the full access-resolution rules (until then only the owner and admin can access a project), and `m2-background-jobs`, which adds job cancellation on delete.
- **Code:** `src/litfoundry/projects/`, `src/litfoundry/catalog/`, `migrations/project/`, `src/litfoundry/cli.py`, frontend Home and workspace screens.
- **API additions not listed in v1.3 §14:** `POST /api/v1/admin/projects/{project_id}/quarantine` and `/release`. v1.3 §16.3 requires quarantine but names no endpoint.
