# Design: M2 project access control

## Context

`m2-project-workspaces` provides projects, with owner and admin access only. This change replaces that stub with the full resolution service, which every later change calls.

## Goals / Non-Goals

**Goals:**
- One authorisation function used by API routes, jobs and download links.
- Audit entries for admin access that can never fail because of the backup write barrier.

**Non-Goals:**
- Role-based access from AD groups (v1.3 §5.1: groups never grant roles).
- Per-object permissions finer than a project.

## Decisions

### Authorisation service
- **Function:** `authorize(user, project_id, action) -> Decision(level, rule)` reads `project_directory` (owner and `public_access`) and `project_acl` in one catalogue query.
- **Actions:**
  - `read`
  - `download`
  - `edit`
  - `run`
  - `export_full`
  - `manage_sharing`
  - `delete_archive`
- **Mapping:** the actions map to levels viewer, editor and owner, with admin above owner.
- **Route integration:** a route decorator `@project_permission("edit")` resolves the project and the decision before the handler runs. It returns 404 when the level is below `read`, and 403 when the project is discoverable but the level is insufficient.
- **Jobs:** the job runner calls `authorize` before start and at each persist checkpoint (implemented in `m2-background-jobs`), using the job's requester.

### Admin access audit
- **Where entries go:** to catalogue `audit_events` with `project_id`, not to the project database. The catalogue `audit_events` table is exempt from the write barrier (v1.3 §16.3), so admin reads never fail during a backup.
- **Openings:** one entry each time the admin requests the project itself (`GET /api/v1/projects/{project_id}`, which the workspace calls when it loads). Requests for records, decisions or artifacts inside an open project are not logged individually, so the audit stays readable while every opening is still recorded, as v1.3 §1 requires.
- **Changes:** every admin mutation inside a project is logged individually.

### Change log
- **Sources:** the project change log merges `project_audit_events` (edits inside the project) with catalogue `audit_events` filtered by `project_id` (sharing, ownership and admin access).
- **Ordering:** results are ordered by timestamp, with a cursor over both sources.

### Lookup rate limit
A token bucket per user of 30 requests per minute, held in memory per process, which is acceptable for a LAN deployment.

## Risks / Trade-offs

- [Admin reads inside an open project are not logged one by one] → Every opening and every change is logged. This granularity is documented in the security notes.
- [The in-memory rate limit is per process] → Acceptable: it limits abuse of the lookup endpoint only.

## Migration Plan

Catalogue revision adding `project_acl`, with a unique `(project_id, user_id)` constraint.
