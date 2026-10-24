# Design: M7 full backup and offline restore

## Context

The M2 primitives exist: the write barrier, the active-writer registry, system leases and quarantine. Project files are write-once (`m2-project-workspaces`). This change implements the snapshot algorithm of v1.3 §16.3 and the restore of §16.5 as CLI commands. The code is structured so `post-v1-scheduled-backups` can call the same `run_full_backup()` from a scheduler and an admin API.

## Goals / Non-Goals

**Goals:**
- Keep the barrier short: database snapshots only.
- Never leave the installation worse off than before a failed backup or restore.

**Non-Goals:**
- Scheduling, retention, rotation, `backup_settings`, admin screens and `/admin/backups/*` (SHOULD).
- Encryption (removed by decision 5).
- Backing up TLS or Caddy CA keys.

## Decisions

### Entry point
- **Function:** `run_full_backup(destination, initiated_by, include_logs) -> BackupRun` in `litfoundry.backups.runner`.
- **CLI:** `backups create` calls it in-process.
- **Stand-alone use:** the command needs no running server. It works against the data root, and coordinates with running server and worker processes through the catalogue barrier and leases when they are up.

### Algorithm
The steps follow v1.3 §16.3.
1. **Inventory:** list projects by state, check path containment and record running jobs and versions.
2. **Barrier:** set the barrier to `draining` and wait for `active_writers` to empty, until the drain timeout (default 120 s), then set it to `frozen`.
3. **Snapshots:** `sqlite3.Connection.backup()` copies the catalogue and each project database into `backup_staging/<run>/`, and each project's file list and sizes are recorded. The barrier is then set to `released`.
4. **Checks and copy:** `PRAGMA integrity_check` and `foreign_key_check` run on the copies. Inventoried files are copied and hashed (SHA-256), and `secret_material/`, configuration and logs are copied.
5. **Manifest:** written as described in the spec.
6. **Archive:** `zipfile.ZipFile(..., allowZip64=True, compression=ZIP_DEFLATED)` writes `<dest>/<name>.zip.partial`. The file is closed, reopened, `testzip()` is run and every entry is compared with the manifest SHA-256 values. The whole-file SHA-256 is computed, then `os.replace` gives the final name and the file is re-stat'ed.
7. **Clean-up:** best-effort deletion of staging.

### Series
The destination path is normalised: absolute, case-folded on Windows, trailing separator removed, UNC kept as UNC. The series ID is the series of the most recent run recorded for that normalised path, or a new UUID if there is none.

### Local staging
`--stage-locally` builds and verifies the archive in `backup_staging/<run>/`, copies it to `<dest>/<name>.zip.partial`, re-hashes the copy against the local SHA-256, then renames it. The free-space check covers both the staging area and the destination.

### Quarantined projects
Their folder is copied file by file without opening SQLite, and flagged in the manifest. Barrier draining ignores them, because they are not writable.

### Destination check
A probe file `.litfoundry-probe-<uuid>` is written, fsync'd and deleted. Free space is checked with `shutil.disk_usage`. The size estimate is the sum of the database and file sizes times 1.1.

### Restore
1. **Pre-checks:** confirm no live processes, using the catalogue heartbeats and leases and a lock file on the data root.
2. **Staging:** extract to `<data_root>/../litfoundry-restore-<run>/`, on the same filesystem as the data root, with validation identical to project import (traversal, ratio, types) plus the manifest checksums.
3. **Data checks:** SQLite checks, then catalogue-to-project consistency.
4. **Migration:** migrate in staging if the archive is older.
5. **Safety backup:** run `run_full_backup` to a sibling safety folder. If that is impossible (no space), stop.
6. **Swap:** rename the live data root to `.pre-restore-<run>`, then rename staging to the live path.
7. **Resets:** generate a new session signing key, clear `jobs` leases, set `queued` jobs to held, mark `running` backup runs `failed` and clear `login_throttle` and `active_writers`.
8. **Smoke checks:** open the catalogue and every project, and decrypt one secret per kind.
9. **Rollback:** on any failure after the swap, swap back. On success, keep the `.pre-restore` folder until the operator removes it, as documented.

- **ACL caveat:** the same-filesystem rename gives atomicity on Windows and POSIX. The data root's ACL is reapplied after the swap.

### Restore test record
Dry runs append one JSON line (time, archive, result) to `<data_root>/logs/restore-tests.jsonl`. They never write to the catalogue or any other live data. `litfoundry status` and Admin → System read the last line to show the last restore test and the 90-day reminder.

## Risks / Trade-offs

- [The data root's parent directory is not writable for staging] → The restore takes a `--staging` option on the same volume, and refuses cross-volume staging for the swap.
- [Large installations make safety backups slow] → Documented, with an estimate shown before confirmation. There is no option to skip the safety backup: if it cannot be taken (for example, no space), the restore stops without changes.
- [The barrier timeout is hit on a busy system] → The backup fails safely. The operator retries, and later the scheduled version retries per policy.

## Migration Plan

Catalogue revision adding `backup_runs`, with the v1.3 §4.1 fields. `series_id` is always set (per destination). `occurrence_key` and `scheduled_for_utc` stay null in v1.
