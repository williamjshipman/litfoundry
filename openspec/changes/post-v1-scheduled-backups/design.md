# Design: Scheduled full backups (post-v1)

## Context

v1 (`m7-full-backup-and-restore`) provides `run_full_backup()`, `backup_runs`, verification and offline restore. This change adds a scheduler, retention and an admin surface around that function, without changing the backup algorithm.

## Goals / Non-Goals

**Goals:**
- Exactly-once scheduled runs under restarts and multiple processes.
- Retention that is provably safe: verified successes only, managed files only, current series only.

**Non-Goals:**
- Web-initiated restore. It stays host-only by design.
- Email notifications (MAY).
- Encryption.

## Decisions

### Scheduler
- **Where it runs:** a coordinator loop in the supervisor-managed worker set. Each worker tries to hold the `backup-scheduler` system lease, which lasts 60 s and is renewed every 20 s. Only the lease holder evaluates the schedule.
- **Library:** APScheduler is not used, because the persisted `next_due_at_utc` plus a 30-second evaluation loop is simpler and fully testable. v1.3 allows either.
- **Occurrence key:** `"<series_id>:<local-date>:<HH:MM>"`. A unique index on `backup_runs.occurrence_key` makes run creation idempotent.
- **Time zones:** the standard-library `zoneinfo` module, with `tzdata` bundled on Windows.
- **Daylight-saving rules:** a gap runs at the first valid local time after it. A repeated hour runs at the first occurrence (`fold=0`).
- **Missed runs:** on each evaluation (including at start), the scheduler lists the occurrences due since `last_attempted_at_utc`. Let `latest` be the most recent of them.
  - If `now - latest <= missed_run_grace_minutes`, one run is created for `latest`.
  - Otherwise no run is created.
  - Every other missed occurrence is logged as skipped, then `next_due_at_utc` is advanced past now.
  - `missed_run_grace_minutes` is an admin setting (default 360, range 0–10080). With grace 0, only an occurrence evaluated exactly on time runs.

### Retention
- **When:** after a run is `completed`, prune the current series.
- **Candidates:** `backup_runs` with `status=completed`, `series_id=current` and `destination_file` present.
- **Checks before deleting:** the file exists, and its manifest's `run_id` and `series_id` match the run.
- **Selection:** sort by `scheduled_for_utc`, falling back to `started_at`. Keep the newest N and delete the rest.
- **Safety:** before any deletion, verify that at least one kept archive is readable and its manifest is valid.
- **Re-registration:** after a restore, the first run scans `*.zip` in the destination root only, not subdirectories. It reads each manifest and upserts `backup_runs` for archives with the current `series_id`.

### Admin API
Thin routes over the v1 functions: `verify_archive()`, `read_manifest()` and the restore dry-run used by `litfoundry restore --dry-run`.

## Risks / Trade-offs

- [Long backups overlap the next due time] → The `full-backup` lease prevents a second run. The skipped occurrence is logged.
- [A network share is unavailable at the due time] → The run fails and retries per policy. Old archives are never pruned on failure.

## Migration Plan

Catalogue revision adding `backup_settings`, plus a unique index on `backup_runs.occurrence_key`.

Configuring a scheduled destination always starts a new series, as v1.3 requires on every destination change. CLI-created archives from v1 keep their own per-destination series, so retention never prunes them, even when they sit in the same directory as scheduled backups.
