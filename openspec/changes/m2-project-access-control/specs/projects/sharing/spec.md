# Spec Delta: projects/sharing

## Purpose

Lets owners and the administrator share projects with every authenticated account or with selected accounts, preview the effect, and see a full change log.

## ADDED Requirements

### Requirement: Visibility modes
`PUT /api/v1/projects/{project_id}/sharing` SHALL let the owner or the administrator set the project's public access to one of these values, shown in the GUI with the labels below:

| Value | GUI label |
|---|---|
| `none` | Private |
| `viewer` | Public view |
| `editor` | Public edit |

Public SHALL mean every authenticated, enabled account of this installation.

#### Scenario: Make public view
- **WHEN** the owner sets visibility to Public view
- **THEN** every signed-in enabled user can discover and read the project

### Requirement: Public edit confirmation
Setting visibility to Public edit SHALL require an explicit confirmation field in the request. The GUI SHALL show a warning before sending it.

#### Scenario: Missing confirmation
- **WHEN** a request sets Public edit without the confirmation field
- **THEN** the request fails with `VALIDATION_ERROR` and visibility is unchanged

### Requirement: Per-user grants
The owner or administrator SHALL be able to add, change and remove per-user `viewer`, `editor` and `deny` entries. Changes SHALL take effect on the affected user's next request.

#### Scenario: Grant editor
- **WHEN** the owner grants `editor` to a colleague on a private project
- **THEN** the colleague can edit the project on their next request

### Requirement: Only owner and admin manage sharing
Sharing changes by anyone other than the owner or administrator SHALL be refused with 403 `FORBIDDEN`.

#### Scenario: Editor changes sharing
- **WHEN** an editor tries to make the project public
- **THEN** the response is 403

### Requirement: Effective permissions preview
`GET /api/v1/projects/{project_id}/sharing` SHALL return the visibility, the explicit entries and each listed account's effective access, with the rule that produced it. The Sharing tab SHALL show this preview.

#### Scenario: Preview with deny
- **WHEN** the owner views sharing for a public project with one denied user
- **THEN** the denied user's effective access is shown as none, due to the explicit deny

### Requirement: User lookup
`GET /api/v1/users/lookup` SHALL return, for authenticated callers, the UUID, display name and username of enabled accounts matching a search term. It SHALL be rate-limited and SHALL NOT return contact emails, roles or account state.

#### Scenario: Lookup for sharing
- **WHEN** an owner searches for "smi"
- **THEN** matching enabled accounts are returned with UUID, display name and username only

### Requirement: Project change log
`GET /api/v1/projects/{project_id}/audit-events` SHALL return, to users with read access, the project's change log, paginated and filterable by actor, action and time. It SHALL cover:
- sharing and ownership changes;
- project edits;
- administrator access to the project.

The Sharing and History tabs SHALL show it.

#### Scenario: Sharing change logged
- **WHEN** the owner changes visibility
- **THEN** the change log shows the actor, old value, new value and time
