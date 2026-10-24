# Tasks: M2 background jobs

## 1. Queue and worker

- [ ] 1.1 Add the catalogue revision for `jobs`, `active_writers` and `job_locked_works`. Verify with migration tests.
- [ ] 1.2 Implement atomic claiming, the lease heartbeat, reclaim on start and lease expiry, and bounded retries with retryable classification. Verify with tests that kill a worker mid-job and assert there is no phantom success (§19 group 10).
- [ ] 1.3 Implement `JobContext` (checkpoint, progress, `authorize`, `write_unit`, temp directory) and a test job type. Verify with unit tests.
- [ ] 1.4 Implement `litfoundry worker` and `litfoundry supervise` (restart on crash, clean shutdown). Verify with process tests on all three CI operating systems.
- [ ] 1.5 Implement idempotency keys. Verify with a double-submit test.
- [ ] 1.6 Implement per-user and global concurrency limits. Verify with a queue test.

## 2. Job API and GUI

- [ ] 2.1 Implement the 202 response helper and `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}` and `POST /api/v1/jobs/{job_id}/cancel` (idempotent), with access rules. Verify with API tests.
- [ ] 2.2 Implement checkpoint cancellation and permission rechecks before start and before persisting. Verify with tests for cancelling a running job and revoking access while queued (§19 group 10).
- [ ] 2.3 Wire project deletion to cancel the project's jobs (`m2-project-workspaces` dependency). Verify with an API test.
- [ ] 2.4 Report job queue health in readiness, `litfoundry status` and the admin system screen. Verify with API and CLI tests.
- [ ] 2.5 Build the job progress component (2–5 s polling, slower when hidden) and recent jobs on Home. Verify with a Playwright test.
- [ ] 2.6 Implement the job state machine (all seven states, including `partial`) and `JOB_FAILED` reporting with the typed cause and a redacted message. Verify with unit tests for each transition and an API test reading a failed job's results.

## 3. Write coordination

- [ ] 3.1 Implement `write_unit()` and the mutating-route decorator, with active-writer registration. Verify with unit tests.
- [ ] 3.2 Implement write scopes, the per-project write lease and the `RECORD_LOCKED` and `PROJECT_BUSY` checks. Verify with API tests during a running `records` job and a `project` job (§19 group 10).
- [ ] 3.3 Implement the global barrier (draining, frozen, released), the drain timeout and the 503 `MAINTENANCE_IN_PROGRESS` with `Retry-After`. Verify with an integration test that raises the barrier during edits and a running job, and asserts that the job pauses and resumes.
- [ ] 3.4 Implement `operational_session()` for exempt tables, with an allowlist test. Verify with a test that sign-in, token refresh, heartbeats and audit writes succeed while frozen.
- [ ] 3.5 Implement fenced system leases with expiry and reclaim. Verify with a stale-lease test.
- [ ] 3.6 Document the job model, write scopes and barrier in `docs/architecture.md`. Verify that the docs list every exempt table.
