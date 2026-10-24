# Spec Delta: platform/audit-log

## Purpose

A tamper-resistant system audit trail of security-relevant and administrative actions, viewable only by the administrator.

## ADDED Requirements

### Requirement: Audit event content
Each system audit event SHALL record a UUID, the acting user's UUID (or `system`), an action name, structured details, an optional project ID and a UTC timestamp. Details SHALL never contain passwords, tokens or secret values.

#### Scenario: Event recorded without secrets
- **WHEN** the administrator resets a user's password
- **THEN** an audit event names the actor, the action and the target user, and contains no password

### Requirement: Audited actions
The system SHALL record an audit event for each of:
- an administrator sign-in;
- a failed sign-in;
- an authentication-settings change;
- creation, update, enabling or disabling of an account;
- a password reset, or a change to the `admin` password;
- a session revocation;
- a privilege change.

#### Scenario: Failed sign-in audited
- **WHEN** a sign-in attempt fails
- **THEN** an audit event records the provider, the identifier as submitted, the source IP and the outcome

### Requirement: Append-only audit trail
No API or GUI action SHALL modify or delete audit events.

#### Scenario: Delete attempt
- **WHEN** any client sends DELETE or PATCH to an audit-event URL
- **THEN** the request is rejected and the event is unchanged

### Requirement: Administrator audit feed
`GET /api/v1/admin/audit-events` SHALL return audit events to the administrator only, paginated and filterable by actor, action, project and time range. Admin → Audit SHALL present the same feed.

#### Scenario: Filter by actor
- **WHEN** the administrator filters the feed by a user UUID
- **THEN** only events by that actor are returned

#### Scenario: Non-admin refused
- **WHEN** a non-admin user calls `GET /api/v1/admin/audit-events`
- **THEN** the response is 403
