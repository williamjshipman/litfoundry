# Tasks: Scheduled full backups (post-v1)

## 1. Settings and destination

- [ ] 1.1 Add the catalogue revision for `backup_settings` and the unique `occurrence_key` index. Verify with migration tests.
- [ ] 1.2 Implement `GET`/`PUT /api/v1/admin/backups/settings` (defaults, including `missed_run_grace_minutes` 360, validation, revision, audit, enabling preconditions, new series on destination change). Verify with API tests, including rejection without a tested destination (§16.6).
- [ ] 1.3 Implement `POST /api/v1/admin/backups/test-destination` (probe only, free space). Verify with tests asserting no other file is read, using mocked Windows UNC, Linux mount, macOS directory and unavailable destinations.

## 2. Scheduler

- [ ] 2.1 Implement the lease-elected coordinator, next-due calculation and occurrence keys. Verify with tests for exactly one run with two worker processes and restart recovery (§16.6).
- [ ] 2.2 Implement daily, weekly and monthly recurrence, daylight-saving gap and overlap handling, missed-run behaviour against the configured grace (within grace runs once, beyond grace skips) and bounded retries. Verify with clock-controlled tests across DST transitions in two time zones (§16.6).
- [ ] 2.3 Run scheduled backups under the system identity, with no secrets in job arguments. Verify with a job-record secret scan.

## 3. Retention

- [ ] 3.1 Implement post-success pruning of verified managed archives in the current series. Verify that with `retain_count=3`, four successes leave three, a later failure leaves the same three, unrelated ZIPs remain and the old destination is not pruned (§16.6).
- [ ] 3.2 Implement the lowered-retention preview, `POST /api/v1/admin/backups/prune` (dry run and apply), protection of the only restore point, and audit. Verify with API tests.
- [ ] 3.3 Implement re-registration after a restore. Verify with a test that restores an older backup and checks that newer archives are re-registered and pruned correctly (§16.6).

## 4. Administration

- [ ] 4.1 Implement `GET`/`POST /api/v1/admin/backups/runs`, `POST .../runs/{run_id}/verify`, `GET .../runs/{run_id}/manifest` and `POST .../runs/{run_id}/restore-check`. Verify with API tests, including a corrupted archive and no live changes.
- [ ] 4.2 Build Admin → Backups (settings with secrets warning, status, history, Run now, Test destination, Verify, Download manifest, guarded Prune now, restore check). Verify with a Playwright test.
- [ ] 4.3 Add dashboard and readiness warnings for failed backups. Verify with an API test.
- [ ] 4.4 Add the non-admin access test across every `/api/v1/admin/backups/` endpoint. Verify that each returns 403 with no leaked detail (§16.6).
- [ ] 4.5 Update the backup documentation for scheduling, retention and the admin screens. Verify that the docs cover each setting.
