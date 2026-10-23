# Spec Delta: data/backup-administration

## Purpose

Gives the administrator, and only the administrator, a console and API to monitor, trigger, verify and inspect full backups and check restores. Live data is never replaced from the web.

## ADDED Requirements

### Requirement: Backups screen
Admin → Backups SHALL show:
- the settings form, with a text path field, Test destination, the resolved path, status, free space and last successful test;
- a warning that backups are unencrypted, contain secrets and need a restricted destination;
- last attempt, last success, next due time, duration, archive size, project count, checksum and error summary;
- the run history.

#### Scenario: Secrets warning
- **WHEN** the administrator opens the backup settings
- **THEN** the destination field is accompanied by the secrets warning

### Requirement: Run history and manual runs
`GET /api/v1/admin/backups/runs` SHALL return run history: size, file name, validation and failure status. `POST` SHALL enqueue an on-demand full backup, recorded with initiator `admin`.

#### Scenario: Run now
- **WHEN** the administrator selects Run backup now
- **THEN** a run with initiator `admin` is queued and its progress is shown

### Requirement: Verify a backup
`POST /api/v1/admin/backups/runs/{run_id}/verify` SHALL check ZIP integrity, manifest checksums and SQLite integrity in temporary staging, without changing live data. Failures SHALL be reported with `BACKUP_VALIDATION_FAILED`.

#### Scenario: Corrupted archive
- **WHEN** the administrator verifies an archive whose content was altered
- **THEN** verification fails with `BACKUP_VALIDATION_FAILED` and live data is unchanged

### Requirement: Download manifest
`GET /api/v1/admin/backups/runs/{run_id}/manifest` SHALL let the administrator download an archive's manifest.

#### Scenario: Manifest download
- **WHEN** the administrator downloads a run's manifest
- **THEN** the manifest JSON for that archive is returned

### Requirement: Restore dry-run check
`POST /api/v1/admin/backups/runs/{run_id}/restore-check` SHALL run the restore verification steps in staging and report the result, without changing live data. The GUI SHALL let the administrator inspect, verify and dry-run backups. Actual restore SHALL remain host-only.

#### Scenario: Web restore impossible
- **WHEN** the administrator runs a restore check from the GUI
- **THEN** a report is shown and no live database or file is replaced

### Requirement: Backup failure visibility
A failed backup SHALL publish an administrator-visible warning on the dashboard and in the readiness endpoint, until a later backup succeeds. An unavailable destination SHALL be reported with `BACKUP_DESTINATION_UNAVAILABLE`.

#### Scenario: Share offline
- **WHEN** the destination share is unreachable at the due time
- **THEN** the run fails with `BACKUP_DESTINATION_UNAVAILABLE` and the dashboard shows a warning

### Requirement: Administrator-only access
Non-admin users SHALL NOT be able to read or change backup settings, trigger backups, see destinations or paths, view backup inventories or audit entries, or perform restore checks, through any endpoint.

#### Scenario: Guessed endpoint
- **WHEN** a non-admin user calls any `/api/v1/admin/backups/` endpoint
- **THEN** the response is 403 and reveals nothing about backups
