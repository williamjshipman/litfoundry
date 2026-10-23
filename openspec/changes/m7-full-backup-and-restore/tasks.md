# Tasks: M7 full backup and offline restore

## 1. Backup

- [ ] 1.1 Add the catalogue revision for `backup_runs`. Verify with a migration test.
- [ ] 1.2 Implement destination validation (absolute, outside the data root, staging, temp and export; UNC accepted), the probe file and the free-space check. Verify with tests for an inside-data-root destination, an unwritable destination and mocked Windows UNC, Linux mount and macOS directory destinations.
- [ ] 1.3 Implement `run_full_backup` steps 1–4: the exclusive lease, the housekeeping pause, the inventory with state rules, barrier-bounded SQLite snapshots, post-release checks, and file copy and hashing. Verify with an integration test that runs a backup during edits, an attachment upload and a search job (§19 group 11).
- [ ] 1.4 Implement the manifest, checksums, configuration metadata and restore README, plus the secrets statement. Verify with a secret scan of logs, manifest and configuration (§19 group 11).
- [ ] 1.5 Implement packaging (ZIP64 and deflate, `.partial`, `testzip`, checksum comparison, SHA-256, rename, existence check), the `--stage-locally` fallback, the branded UTC filename and the per-destination series ID in the run record and manifest. Verify with tests that the filename matches the manifest, that a locally staged archive is re-verified at the destination, and that two backups to one destination share a series ID.
- [ ] 1.6 Implement failure handling (redacted errors, admin alert, staging cleanup, earlier archives untouched) and the error-state and quarantine rules. Verify with corrupted-database, missing-file, full-disk and drain-timeout tests (§19 group 11).
- [ ] 1.7 Implement `litfoundry backups create`, `verify` and `list`, the licensed-content warning, and backup status in `status`, readiness and the admin system screen. Verify with CLI tests, including verification of a tampered manifest.
- [ ] 1.8 Implement stale `.partial` housekeeping. Verify with a test.

## 2. Restore

- [ ] 2.1 Implement the restore pre-checks (no live processes), staging validation, SQLite and consistency checks, and migration of older archives. Verify with tests for a running service, a missing project folder and an older archive.
- [ ] 2.2 Implement `--dry-run` (no change to live data, appends to `logs/restore-tests.jsonl`) and `--confirm` (outage warning, interactive confirmation). Show the last restore test, and a reminder after 90 days, in `litfoundry status` and Admin → System. Verify with CLI tests and a clock-controlled reminder test.
- [ ] 2.3 Implement the mandatory safety backup (restore stops if it cannot be taken), rename swap, post-restore resets (signing-key rotation, leases, held jobs, failed backup runs, throttles) and smoke checks with rollback. Verify with an interrupted-restore rollback test (§19 group 11).
- [ ] 2.4 Add a cross-OS restore test: create a backup on the Windows CI runner, restore it on the Linux runner, and assert users, ACLs, projects, reports, credentials and forced re-sign-in, with at least two users, an AD configuration, multiple projects and pending jobs (§16.5). Verify that it passes in CI.

## 3. Documentation

- [ ] 3.1 Write the backup and restore guides (same machine and new machine, Windows, Linux and macOS; destination permissions; unencrypted-secrets warning; environment dependencies; quarterly restore test). Verify that each CLI option is documented.
- [ ] 3.2 Record in `docs/decisions.md` that the §16.5 admin restore GUI is deferred to `post-v1-scheduled-backups`. Verify that the entry exists.
