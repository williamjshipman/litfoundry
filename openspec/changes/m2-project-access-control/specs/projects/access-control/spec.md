# Spec Delta: projects/access-control

## Purpose

Decides who can do what in each project, consistently, on every request, job and download. The administrator has full but audited access.

## ADDED Requirements

### Requirement: Read rights
Viewers, editors, owners and the administrator SHALL be able to discover and read a project and download its permitted result tables and figures.

#### Scenario: Viewer reads
- **WHEN** a user with viewer access opens a project and downloads a result table
- **THEN** both succeed

### Requirement: Edit rights
Editors, owners and the administrator SHALL be able to edit the search strategy, records and screening, and to run searches and analyses. Viewers SHALL be refused with 403 `FORBIDDEN`.

#### Scenario: Viewer attempts edit
- **WHEN** a viewer submits a screening decision
- **THEN** the response is 403 and nothing is stored

### Requirement: Owner rights
Only the owner and the administrator SHALL be able to:
- export the full project ZIP, including raw data;
- manage sharing and ownership;
- archive or delete the project.

Editors SHALL be refused with 403 `FORBIDDEN`.

#### Scenario: Editor attempts export
- **WHEN** an editor requests a full project export
- **THEN** the response is 403

### Requirement: Access resolution order
Effective access SHALL be resolved in this order, with the first match winning:
1. the administrator, who has full access;
2. the owner;
3. an explicit per-user entry (`editor`, `viewer` or `deny`);
4. the project's public default (`editor`, `viewer` or none);
5. otherwise, no access.

#### Scenario: Explicit viewer on public-edit project
- **WHEN** a project is Public edit and a user has an explicit `viewer` entry
- **THEN** that user has viewer access only

### Requirement: Explicit deny
An explicit `deny` entry SHALL remove access that the public default would otherwise grant. It SHALL never apply to the administrator.

#### Scenario: Denied on public project
- **WHEN** a user has a `deny` entry on a Public view project
- **THEN** the project is absent from the user's listing and direct requests fail

#### Scenario: Deny ignored for admin
- **WHEN** the owner adds a `deny` entry for `admin`
- **THEN** the entry is rejected or ignored and the administrator keeps full access

### Requirement: Disabled accounts denied
A disabled account SHALL have no access to any project, whatever its ownership, ACL entries or the public default.

#### Scenario: Disabled owner
- **WHEN** the owner of a project is disabled
- **THEN** no session of that account can read the project

### Requirement: No anonymous access
Unauthenticated callers SHALL NOT discover or read any project data.

#### Scenario: Anonymous request
- **WHEN** an unauthenticated client requests a public project
- **THEN** the response is 401

### Requirement: Undiscoverable projects are not found
A request for a project the caller cannot discover SHALL receive 404 `NOT_FOUND`, so private project existence is not revealed. A caller who can discover the project but lacks the needed right SHALL receive 403 `FORBIDDEN`.

#### Scenario: Private project probed
- **WHEN** a user requests another user's private project by UUID
- **THEN** the response is 404

### Requirement: Audited administrator access
The system SHALL record an audit event with the project ID in the system audit log each time:
- the administrator opens a project they do not own, meaning a request for the project itself (`GET /api/v1/projects/{project_id}`, as when the workspace loads), not each request inside it;
- the administrator makes a change inside such a project.

These entries SHALL always succeed, including while a maintenance write barrier is in place.

#### Scenario: Admin opens a user's project
- **WHEN** the administrator opens a project owned by another user
- **THEN** a system audit event records the access with the project ID

#### Scenario: Admin opens the same project twice
- **WHEN** the administrator opens the same project twice in one session
- **THEN** two audit events are recorded

### Requirement: Enforcement at every entry point
Permissions SHALL be checked:
- on every project API request;
- when a background job is enqueued, before it starts and before it persists results;
- when a download link is generated and again when it is used.

Revoked access SHALL take effect on the next check.

#### Scenario: Access revoked while job queued
- **WHEN** an editor's access is revoked while their analysis job is queued
- **THEN** the job does not run and records a permission failure

#### Scenario: Download after revocation
- **WHEN** a user's access is revoked after a download link was generated
- **THEN** using the link is refused
