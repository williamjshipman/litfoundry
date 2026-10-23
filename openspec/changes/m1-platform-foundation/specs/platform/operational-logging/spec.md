# Spec Delta: platform/operational-logging

## Purpose

Provides structured operational logs that support diagnosis and correlation across requests and jobs, while never exposing secrets or private content.

## ADDED Requirements

### Requirement: Structured log entries
Every log entry SHALL be structured and include a UTC timestamp, level, process name and event name. Where they apply, it SHALL also include the request ID, job ID, project ID and user ID.

#### Scenario: Request correlation
- **WHEN** an API request fails
- **THEN** the log entry for the failure contains the same `request_id` that the error response returned to the client

### Requirement: Log location
Logs SHALL be written under `<data_root>/logs/` with a bounded total size, rotating older files.

#### Scenario: Rotation bound
- **WHEN** the log size limit is reached
- **THEN** the oldest log file is rotated out and total log size stays within the configured bound

### Requirement: Log redaction
Log entries SHALL NOT contain passwords, API keys, the service-account password, session or refresh tokens, CSRF tokens, bootstrap tokens, raw full-text content or full LDAP payloads.

#### Scenario: Failed sign-in logged safely
- **WHEN** a sign-in attempt fails
- **THEN** the log entry records the provider, the resolved user ID if known and the outcome, without the submitted password

### Requirement: Admin log view
The administrator console SHALL show recent log entries, filterable by level, process and correlation ID. Other users SHALL have no access to logs.

#### Scenario: Admin views logs
- **WHEN** the administrator filters the log view by a `request_id`
- **THEN** only entries carrying that ID are shown

#### Scenario: User cannot view logs
- **WHEN** a non-admin user requests the log view or its API
- **THEN** access is denied
