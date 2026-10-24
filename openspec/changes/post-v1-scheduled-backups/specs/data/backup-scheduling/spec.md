# Spec Delta: data/backup-scheduling

## Purpose

Runs full-installation backups automatically on an administrator-defined schedule, exactly once per occurrence, without requiring anyone to be signed in.

## ADDED Requirements

### Requirement: Backup settings
`GET` and `PUT /api/v1/admin/backups/settings` SHALL let only the administrator view and change:
- `enabled`;
- `frequency` (`daily`, `weekly` or `monthly`) and `local_time_hhmm`;
- `iana_timezone`;
- `weekday` or `monthday` (1–28);
- `destination_server_path`;
- `retain_count`;
- `include_logs`;
- `missed_run_grace_minutes` (0–10080).

Every change SHALL be validated, increment the settings revision and record an audit event.

#### Scenario: Invalid month day
- **WHEN** the administrator sets a monthly schedule with month day 31
- **THEN** the change is rejected with `VALIDATION_ERROR`

#### Scenario: Non-admin
- **WHEN** a non-admin user reads or changes backup settings
- **THEN** the response is 403 and no setting or path is revealed

### Requirement: Settings defaults
Before the administrator configures backups, the settings SHALL default to:
- `enabled` false;
- `frequency` daily;
- `include_logs` true;
- the server's detected time zone, shown explicitly;
- `missed_run_grace_minutes` 360;
- no destination.

The settings form SHALL suggest 7 as the first `retain_count`.

#### Scenario: Fresh installation
- **WHEN** the administrator first opens the backup settings
- **THEN** backups are disabled, no destination is set and retention 7 is suggested

### Requirement: Enabling preconditions
Scheduled backups SHALL be enabled only when all of these hold:
- the current destination has passed a destination test;
- `retain_count` is at least 1;
- the recurrence and time zone are valid.

#### Scenario: Untested destination
- **WHEN** the administrator enables backups for a destination that has not passed a test
- **THEN** the request fails with `VALIDATION_ERROR`

### Requirement: Destination rules and test
The destination SHALL be an absolute server-side path outside the data root, and not equal to or beneath any staging, temp or export path. It SHALL accept Windows UNC paths and mounted directories.

`POST /api/v1/admin/backups/test-destination` SHALL write and delete a uniquely named probe file, and report the resolved path, status and free space where available. It SHALL never read or list other files.

#### Scenario: Probe only
- **WHEN** the administrator tests a destination that contains other files
- **THEN** only the probe file is created and deleted, and no other file is read

### Requirement: Destination change starts a new series
Changing the destination SHALL assign a new backup series ID.

#### Scenario: New destination
- **WHEN** the administrator changes the destination
- **THEN** later backups belong to a new series

### Requirement: Next-due calculation
The system SHALL persist the next due time and the last attempted time in UTC. Explicit schedule edits SHALL recalculate the next due occurrence and record the settings revision.

#### Scenario: Time changed
- **WHEN** the administrator changes the daily time from 23:00 to 02:00
- **THEN** the next due time is recalculated for 02:00 in the configured time zone

### Requirement: Single scheduler
Exactly one process SHALL coordinate the schedule at a time, elected through an expiring, fenced lease. Schedules SHALL never be registered separately per web thread or per worker process.

#### Scenario: Two workers
- **WHEN** two worker processes are running at a due time
- **THEN** exactly one backup run is created for that occurrence

### Requirement: Exactly-once occurrences
At each due time, the scheduler SHALL acquire the `full-backup` lease and create one run with a unique occurrence key, then enqueue the backup job. Restarts, clock adjustments and multiple processes SHALL never produce a second run for the same occurrence.

#### Scenario: Restart at due time
- **WHEN** the service restarts just after a scheduled backup started
- **THEN** no second run is created for that occurrence

### Requirement: System identity
Scheduled backups SHALL run under the system service identity without an administrator signed in. Secrets SHALL never appear in job arguments or logs.

#### Scenario: Nobody signed in
- **WHEN** a backup falls due overnight with no sessions active
- **THEN** it runs and is recorded with initiator `schedule`

### Requirement: Missed runs
When the scheduler finds missed occurrences (at service start or whenever the schedule is evaluated late), it SHALL run exactly one backup for the most recent missed occurrence if its due time is no more than the administrator-configured `missed_run_grace_minutes` in the past. Older missed occurrences SHALL be logged as skipped and not run. At most one overdue backup SHALL run, after which the next due time SHALL be advanced past now.

#### Scenario: Restart within grace
- **WHEN** a daily 23:00 backup was missed, the grace is 360 minutes and the service restarts at 01:30
- **THEN** one backup runs at restart for the 23:00 occurrence

#### Scenario: Restart beyond grace
- **WHEN** the most recent missed occurrence is 10 hours old and the grace is 360 minutes
- **THEN** no catch-up backup runs, the missed occurrences are logged as skipped and the next backup runs at its normal time

#### Scenario: Several occurrences missed
- **WHEN** three daily occurrences were missed and the most recent is within the grace
- **THEN** one backup runs for the most recent occurrence and the two earlier ones are logged as skipped

### Requirement: Daylight saving
Each due local day SHALL produce exactly one run. A local time that does not exist on the day SHALL run at the first valid time after it. A local time that occurs twice SHALL run at its first occurrence. The computed UTC time SHALL be recorded.

#### Scenario: Spring-forward gap
- **WHEN** the scheduled local time falls in a daylight-saving gap
- **THEN** one backup runs at the first valid time after the gap, with its UTC time recorded

### Requirement: Bounded retries
A failed scheduled backup SHALL be retried only according to the configured bounded retry policy.

#### Scenario: Retry limit
- **WHEN** a scheduled backup fails more times than the retry limit
- **THEN** no further attempts are made for that occurrence and the failure is shown to the administrator
