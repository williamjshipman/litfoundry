# Spec Delta: projects/project-lifecycle

## Purpose

Governs a research project's life from creation through archiving, transfer, quarantine and two-stage deletion, and the screens that let users find and open projects.

## ADDED Requirements

### Requirement: Create a project
`POST /api/v1/projects` SHALL create a project owned by the caller from a title and optional description, objectives and research questions. The project SHALL become usable only after it reaches state `ready`.

#### Scenario: Successful creation
- **WHEN** a signed-in user creates a project titled "Flotation digital twins"
- **THEN** the response returns the project UUID with state `ready` and the caller as owner

### Requirement: Failed provisioning leaves nothing behind
If provisioning fails at any step, the system SHALL remove the staging folder and the catalogue entry and return an error. The `error` state SHALL be reserved for an existing project later found to be damaged.

#### Scenario: Provisioning failure
- **WHEN** creating the project database fails during provisioning
- **THEN** the caller receives an error, no catalogue entry remains and no project folder remains

### Requirement: List projects
`GET /api/v1/projects` SHALL return, paginated and filterable by ownership, state and title text, the projects the caller can discover:
- projects the caller owns;
- projects shared with the caller;
- public projects.

The administrator SHALL see every project.

#### Scenario: Owner sees own private project
- **WHEN** a user lists projects
- **THEN** their private projects are included and other users' private projects are not

#### Scenario: Admin sees all
- **WHEN** the administrator lists projects
- **THEN** every project in the catalogue is listed with its state

### Requirement: View and update project details
`GET /api/v1/projects/{project_id}` SHALL return the project's details, state, owner and revision. `PATCH` SHALL update title, description, objectives and research questions for callers with edit rights, using `If-Match` optimistic concurrency.

#### Scenario: Stale update
- **WHEN** an editor submits a PATCH with an outdated revision
- **THEN** the response is 409 `CONFLICT` and nothing changes

### Requirement: Archive and unarchive
The owner or the administrator SHALL be able to archive a project with `POST /api/v1/projects/{project_id}/archive`, and reverse it with `POST /api/v1/projects/{project_id}/unarchive`. An archived project SHALL be read-only: any mutation SHALL be refused with 409 `CONFLICT` detail `PROJECT_ARCHIVED`.

#### Scenario: Edit archived project
- **WHEN** an editor tries to change an archived project
- **THEN** the change is refused and the project is unchanged

### Requirement: Two-stage deletion
`DELETE /api/v1/projects/{project_id}` by the owner or administrator SHALL require explicit confirmation, then:
1. mark the project `deleting` and revoke access;
2. cancel its jobs and wait a bounded time for in-flight operations;
3. move the folder to `<data_root>/trash/`.

The GUI SHALL offer a project export before confirming.

#### Scenario: Delete project
- **WHEN** the owner confirms deletion
- **THEN** the project disappears from every listing and its folder is in `trash/`

#### Scenario: Delete without confirmation
- **WHEN** a DELETE request lacks the confirmation parameter
- **THEN** the request fails with `VALIDATION_ERROR` and nothing changes

### Requirement: Trash purge
Housekeeping SHALL permanently delete trashed project folders after a configurable retention period, and SHALL record each purge in the audit log.

#### Scenario: Retention elapsed
- **WHEN** a trashed project is older than the retention period
- **THEN** housekeeping deletes its folder and records an audit event

### Requirement: Unavailable project states
Requests to open a project in state `deleting`, `quarantined` or `error`, or one whose schema version is not current, SHALL be refused with 409 `PROJECT_UNAVAILABLE`. The exception is administrator repair and quarantine actions.

#### Scenario: Quarantined project
- **WHEN** a user opens a quarantined project
- **THEN** the response is 409 `PROJECT_UNAVAILABLE`

### Requirement: Transfer ownership
`POST /api/v1/projects/{project_id}/transfer-ownership` by the owner or administrator SHALL make another active account the owner, without moving any project files. Afterwards the previous owner's access SHALL follow the sharing rules.

#### Scenario: Transfer
- **WHEN** the owner transfers a project to another user
- **THEN** the other user is the owner and the project folder path is unchanged

### Requirement: Transfer all of a user's projects
`POST /api/v1/admin/users/{user_id}/transfer-projects` SHALL let the administrator transfer every project owned by one account to another active account in a single action, recording an audit event per project.

#### Scenario: Disabled user's projects
- **WHEN** the administrator transfers all projects of a disabled user to a colleague
- **THEN** the colleague owns each of those projects

### Requirement: Quarantine damaged projects
The administrator SHALL be able to quarantine a project with `POST /api/v1/admin/projects/{project_id}/quarantine`, and return it to `ready` with `/release` after repair. A quarantined project SHALL be unavailable to users.

#### Scenario: Quarantine and release
- **WHEN** the administrator quarantines a damaged project and later releases it after repair
- **THEN** users cannot open it while quarantined and can open it again after release

### Requirement: Damaged project detection
When the system finds that an existing project's database fails an integrity check, it SHALL set the project to `error`, refuse normal use and notify the administrator in the application.

#### Scenario: Corrupt database found
- **WHEN** opening a project finds its database corrupt
- **THEN** the project state becomes `error` and an admin-visible alert is raised

### Requirement: Home page
The Home page SHALL show the caller's owned projects, the projects shared with them and the other projects visible to them, as cards or a table, with filters and a create button. The administrator SHALL see all projects.

#### Scenario: Home groups
- **WHEN** a user with owned and shared projects opens Home
- **THEN** owned and shared projects appear in separate groups

### Requirement: Project workspace
Opening a project SHALL show a workspace with an Overview tab, showing title, aims, research questions, owner, state and revision. Each feature area SHALL have its own tab, with History/settings last.

#### Scenario: Open workspace
- **WHEN** a user with read access opens a project
- **THEN** the Overview tab shows the project's details

### Requirement: New project wizard
The new-project wizard SHALL start with a project-details step (title, aims, research questions) and create the project when that step is completed.

#### Scenario: Wizard creates project
- **WHEN** a user completes the project-details step
- **THEN** the project is created and its workspace opens
