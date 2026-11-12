# Proposal: M2 project access control

## Why

Projects are shared between colleagues on one installation. "Public" means visible to every authenticated account, never to anonymous users. Owners need per-user exceptions, including an explicit deny. The administrator has full, audited access everywhere (v1.3 §1, decisions 2 and 9; §6). These rules must be enforced on every API call, background job and download before any research data is stored.

## What Changes

- **Rights matrix:** viewer, editor, owner and admin, as in v1.3 §1.
- **Access resolution order:**
  1. admin;
  2. owner;
  3. explicit ACL (`editor`, `viewer` or `deny`);
  4. public default;
  5. otherwise, deny.

  A disabled account is always denied.
- **Audited admin access:** the admin's access to projects is audited in the catalogue `audit_events` table, including opening projects the admin does not own and every change.
- **Enforcement points:** every project endpoint, background job and download link checks permissions. Anonymous access is never allowed.
- **Sharing:**
  - visibility can be Private, Public view or Public edit;
  - Public edit requires confirmation;
  - per-user grants and denies;
  - an effective-permissions preview;
  - a project change log;
  - a rate-limited user lookup for the sharing dialog.

## Capabilities

### New Capabilities

- `projects/access-control`: the rights matrix, resolution order, admin access auditing and enforcement points.
- `projects/sharing`: visibility modes, per-user grants and denies, the permission preview, user lookup and the project change log.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §1: decisions 2 and 9, the roles, and the project rights and access resolution;
  - §4.1: the `project_acl` table;
  - §6;
  - §13: Sharing;
  - §14: `/projects/{project_id}/sharing`, `/projects/{project_id}/audit-events` and `/users/lookup`;
  - §19: group 2 (ACL matrix) and group 3 (forged access);
  - §20: M2.
- **Depends on:** `m2-project-workspaces`.
- **Code:** `src/litfoundry/auth/authorization.py`, `src/litfoundry/projects/sharing.py`, the API routes, and the Sharing tab and user lookup in the GUI.
- **Later work:** later changes call the shared authorisation service for their endpoints, jobs and downloads. Their own tests cover their routes.
