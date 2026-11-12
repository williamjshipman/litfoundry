"""Security Model and Access Control Documentation.

This document describes the security model for LitFoundry, including access control,
authentication, and audit logging.
"""

# Security Model

## Trust Model

LitFoundry operates with a **single-administrator trust model**. The built-in `admin` user
is fully trusted and can:

- Read and modify any project, regardless of ownership or visibility
- Create and delete users
- Access system configuration
- View all audit logs

Users are authenticated but not fully trusted. They can:
- Own and manage their own projects
- Collaborate on projects shared with them
- Access only projects they own or that have been shared with appropriate permissions

Non-authenticated users have no access to any project data or functionality.

## Access Control

### Access Levels

Projects have four access levels:

1. **Viewer** - Read-only access. Users can:
   - Discover and view the project
   - Download result tables and figures
   - Cannot make any modifications

2. **Editor** - Edit access. Users can:
   - Do everything a viewer can do
   - Edit the search strategy and screening criteria
   - Run searches and analyses
   - Record screening decisions
   - Cannot delete the project or modify sharing

3. **Owner** - Full access. Users can:
   - Do everything an editor can do
   - Export the full project ZIP with all raw data
   - Modify project sharing and transfer ownership
   - Archive and delete the project

4. **Admin** - System access. The admin user has:
   - Full access to any project
   - Audited access (all admin access to non-owned projects is logged)

### Access Resolution Order

When evaluating whether a user can perform an action on a project, the system checks
in this order:

1. **Disabled accounts are always denied** - If the user's account is disabled, all access
   is denied regardless of other rules.

2. **Admin privilege** - If the user is the system admin, they get full access.

3. **Owner** - If the user owns the project, they get full access.

4. **Explicit ACL** - If there is an explicit per-user access control entry:
   - `editor` role grants editor access
   - `viewer` role grants viewer access
   - `deny` role removes access (overrides public default)

5. **Public default** - If the project is public:
   - Public view grants viewer access to all authenticated users
   - Public edit grants editor access to all authenticated users

6. **Otherwise deny** - If none of the above rules apply, the user has no access.

### Visibility Modes

Projects can be set to one of three visibility modes:

| Mode | API Value | GUI Label | Access Level | Who Can See |
|------|-----------|-----------|--------------|-------------|
| Private | `none` | Private | Owner only | Owner and admin only |
| Public View | `viewer` | Public view | Viewer | All authenticated users (unless explicitly denied) |
| Public Edit | `editor` | Public edit | Editor | All authenticated users (unless explicitly denied) |

Setting a project to Public Edit requires an explicit confirmation in the GUI to prevent
accidental exposure.

### Explicit Deny

An explicit `deny` ACL entry removes access that would otherwise be granted by the public
default. It does not apply to the admin user (who always has full access) or to the project
owner.

## Admin Access Auditing

Admin users have full access to all projects, but this access is audited. The following
events are logged to the system audit trail:

### Project Opening

Every time an admin user requests a project they do not own, an audit event is recorded
with:
- `action`: `project_opened`
- `resource_type`: `project`
- `resource_id`: the project UUID
- `actor_user_id`: the admin user's ID
- `timestamp`: when the access occurred

This event is logged once per project opening (via `GET /api/v1/projects/{project_id}`),
not for each subsequent request inside an open project. This keeps the audit log readable
while still recording that the admin accessed the project.

### Project Changes

Every admin modification inside a non-owned project is logged individually:
- `action`: specific action (e.g., `search_ran`, `screening_recorded`)
- `resource_type`: the resource type (e.g., `screening_decision`)
- `resource_id`: the specific resource's UUID
- `details`: information about the change
- `actor_user_id`: the admin user's ID
- `timestamp`: when the change occurred

### Access Denial

If an admin's access is revoked while an operation is in progress (e.g., a long-running
analysis job), the operation fails with a permission error and is logged.

### Non-Owned Project Distinction

Admin access to projects they own is not audited individually (just like regular user
access). Only access to projects owned by other users is audited, since that is the
sensitive operation.

## Audit Events

All sensitive operations are recorded in the audit log (`audit_events` table):

### Catalogue Audit Events

Catalogue events track system-wide operations:
- User creation, updates, and deletion
- Authentication and authorization failures
- Admin configuration changes
- Sharing and access control changes
- Admin access to non-owned projects

### Project Audit Events

Project events track operations within specific projects:
- Search strategy changes
- Record imports and screening
- Analysis execution
- Result exports

Users with read access to a project can view the project's audit log via
`GET /api/v1/projects/{project_id}/audit-events`, which merges both catalogue
(sharing/admin) and project-specific events.

## Rate Limiting

User lookup (`GET /api/v1/users/lookup`) is rate-limited to prevent abuse:
- **Limit**: 30 requests per minute per user
- **Window**: Sliding window, per-process in-memory
- **Response**: HTTP 429 if limit exceeded

This rate limit is acceptable for a LAN deployment where users are internal colleagues.

## Policy Enforcement

Permissions are checked:

- On every project API request (before the handler runs)
- When background jobs are enqueued, started, and when they persist results
- When download links are generated and when they are used
- When archiving or deleting projects

Revoked access takes effect on the next check. Users cannot bypass revocation by
using cached credentials or previously-generated download links.

## Data Protection

- **Passwords**: Hashed with Argon2id (salted, resistant to GPU attacks)
- **Sessions**: Signed with `HS512`, sent as HTTP-only cookies, double-submit CSRF protection
- **Secrets**: Encrypted at rest with AES-256-GCM (AD credentials, API keys)
- **Transport**: TLS 1.2+ required (enforced by Caddy reverse proxy)

## Implementation

The access control system is implemented in `litfoundry/auth/authorization.py`:

```python
from litfoundry.auth.authorization import authorize, AccessLevel

# Check user access to a project
decision = authorize(user, project_id, db_session)

# Check if user can perform an action
if decision.allows_action(AccessLevel.EDITOR):
    # User has editor access or higher
    ...
```

API routes use the `@project_permission` decorator:

```python
@bp.route("/<project_id>/edit", methods=["POST"])
@project_permission(AccessLevel.EDITOR)
def edit_project(project_id):
    # Access is already verified; the user has editor access or higher
    ...
```

## About This Installation

Every LitFoundry installation displays the trust model in its About screen. The statement
is set during initialization and cannot be modified without a factory reset:

> The administrator can read and change every project, without exception.
> Do not use this installation for confidential research data unless you fully trust
> the administrator.

This statement is served from the `/api/v1/system/about` endpoint and embedded in the GUI.
