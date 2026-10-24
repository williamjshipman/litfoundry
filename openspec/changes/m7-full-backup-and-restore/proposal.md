# Proposal: M7 full backup and offline restore

## Why

An installation holds every user's research, so it needs disaster recovery. A full backup must be consistent across the catalogue, every project database and every project file. It must restore on another machine without extra steps, so it includes the stored secrets. Because it is unencrypted, the destination must be protected (v1.3 §16 and decision 5). In v1, full backups and restores are run from the host CLI. Scheduling, retention and the admin backup screens are SHOULD (v1.3 §0.2, in `post-v1-scheduled-backups`).

## What Changes

- **`litfoundry backups create --destination PATH`:**
  - the destination is required (there is no default), absolute and outside the data root, and is checked first;
  - the backup takes an exclusive `full-backup` lease, pausing housekeeping and conflicting with migration and restore;
  - the global write barrier is raised only while the SQLite online snapshots run;
  - the snapshots are checked, then the inventoried files are copied and hashed;
  - `secret_material/` is included;
  - the manifest carries checksums and states that the archive contains secrets;
  - the archive is named `litfoundry_full_<YYYYMMDD_HHMMSSZ>_<run_uuid_short>.zip` and written as `.partial`, verified, then renamed;
  - runs are recorded in `backup_runs`.
- **Project states in a backup:** quarantined projects are included as flagged raw copies, and a project in `error` fails the backup.
- **Failures:** a failed run deletes no earlier backup and raises an admin alert.
- **`litfoundry backups verify` and `litfoundry backups list`.**
- **`litfoundry restore --archive PATH --dry-run|--confirm`:**
  - runs offline, refusing while the service runs;
  - full verification and staging, migration of older archives, a safety backup and rollback-capable replacement;
  - the session signing key is rotated, leases cleared, queued jobs held for review and stale backup runs failed;
  - smoke checks run before writes are accepted.
- **No web restore:** no web endpoint replaces live data.
- **Status and documentation:**
  - backup and restore status, with a quarterly restore-test reminder;
  - same-machine and new-machine restore guides for each OS.

## Capabilities

### New Capabilities

- `data/full-backup`: consistent full-installation backups from the CLI, with verification, listing, failure handling and status.
- `data/full-restore`: verified offline restore, with dry run, rollback and post-restore resets.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.2: v1 backups from the CLI;
  - §4.1: the `backup_runs` table;
  - §16: introduction and release scope;
  - §16.1: the destination rules and filename format only;
  - §16.3;
  - §16.5;
  - §16.6: the CLI-applicable tests;
  - §17: the backup bullet;
  - §18.1: `backups` and `restore`;
  - §19: group 11 (full-system backup);
  - §20: M7 and the definition of done.
- **Depends on:** `m2-background-jobs` (barrier, leases), `m2-project-workspaces` (quarantine, migrations) and `m7-project-export-import` (export exclusion from backups).
- **Code:** `src/litfoundry/backups/` and the CLI commands.
- **Out of scope (SHOULD, `post-v1-scheduled-backups`):**
  - scheduling;
  - retention and rotation;
  - `backup_settings`;
  - the Admin → Backups screens;
  - the `/admin/backups/*` endpoints;
  - the admin GUI for inspect, verify and dry-run.

  v1.3 §16.5 mentions that GUI, but §0.2 makes v1 backups CLI-only. The GUI is therefore deferred, and the decision is recorded.
