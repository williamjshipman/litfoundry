# Proposal: Scheduled full backups with retention and admin screens (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Do not start before the v1 changes are archived.

## Why

v1 provides consistent full backups and offline restore from the host CLI. Administrators then need these to happen reliably without host access:
- on a schedule, with exactly-once semantics and predictable behaviour across restarts and daylight-saving changes;
- with count-based retention that never deletes the only good restore point;
- managed from the administrator console (v1.3 decision 8, §16.1, §16.2 and §16.4).

## What Changes

- **Backup settings** (`/admin/backups/settings`):
  - enabled, frequency (daily, weekly or monthly), local time, IANA time zone, weekday or month day (1–28), destination, retention count, include-logs and the missed-run grace period;
  - enabling requires a tested destination;
  - a destination change starts a new retention series.
- **Destination test** (`/admin/backups/test-destination`) using a probe file.
- **Scheduler:**
  - a single lease-elected coordinator with a persisted next-due time;
  - exactly one run per occurrence, keyed by occurrence;
  - runs under the system identity;
  - at most one overdue run after downtime, only when the latest missed occurrence is within an admin-configured grace period;
  - deterministic daylight-saving handling;
  - bounded retries.
- **Retention:**
  - rotation only after a verified success;
  - only managed archives of the current series are pruned, never unrelated files or old destinations;
  - a preview when retention is lowered, and a guarded Prune now (`/admin/backups/prune`);
  - the only valid restore point is protected;
  - managed archives are re-registered after a restore.
- **Admin → Backups:**
  - status, history, Run now (`/admin/backups/runs`), Verify (`.../verify`), Download manifest (`.../manifest`) and restore dry-run checks (`.../restore-check`);
  - the admin GUI for inspecting, verifying and dry-running restores that v1.3 §16.5 describes;
  - failure warnings on the dashboard.

## Capabilities

### New Capabilities

- `data/backup-scheduling`: backup settings, destination testing and the exactly-once scheduler.
- `data/backup-retention`: series-based, verified-only retention, pruning and post-restore re-registration.
- `data/backup-administration`: admin backup screens and endpoints, verification, manifests, restore checks and access restrictions.

### Modified Capabilities

None. The v1 `data/full-backup` and `data/full-restore` requirements still hold. Scheduled and admin-initiated runs reuse the same backup procedure.

## Impact

- **v1.3 sections implemented:**
  - §4.1: the `backup_settings` table, and the scheduling fields of `backup_runs`;
  - §13: Admin backups;
  - §14: the `/admin/backups/*` routes, `BACKUP_DESTINATION_UNAVAILABLE` and `BACKUP_VALIDATION_FAILED`;
  - §16.1, §16.2 and §16.4;
  - §16.5: the admin GUI;
  - §16.6: the scheduling, retention and admin tests.
- **Depends on:** `m7-full-backup-and-restore` and `m2-background-jobs`.
- **Code:** `src/litfoundry/backups/scheduler.py` and `retention.py`, the admin API routes and the Admin → Backups screens.
