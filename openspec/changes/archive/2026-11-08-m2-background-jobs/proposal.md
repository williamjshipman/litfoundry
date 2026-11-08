# Proposal: M2 background jobs

## Why

Searches, imports, deduplication, analyses, exports and backups are long-running. They must run outside web request threads, survive restarts, be cancellable and never corrupt project databases (v1.3 §9). The full-backup write barrier and job write scopes coordinate every writer. v1.3 §20 requires this backup foundation from M2, so it is not deferred until launch.

## What Changes

- **Job queue:** a catalogue-backed queue with job states, leases and heartbeats, reclaim on restart, idempotency keys, bounded retries and checkpoint cancellation.
- **Processes:** `litfoundry worker` runs jobs, and `litfoundry supervise` runs the server and workers under one supervisor.
- **Job API:** the `202 Accepted` pattern for long operations, plus `/jobs`, `/jobs/{job_id}` and `/jobs/{job_id}/cancel`.
- **GUI:** job progress polling and recent jobs on Home.
- **Safety and limits:** permission rechecks before a job starts and before it persists results, and per-user and global concurrency limits.
- **Write coordination:**
  - write scopes (`append`, `records`, `project`) and a per-project write lease;
  - `409 RECORD_LOCKED` and `409 PROJECT_BUSY` for interactive edits that conflict with a running job;
  - the global write barrier, with an active-writer registry, `503 MAINTENANCE_IN_PROGRESS` and exempt operational writes;
  - fenced system leases for maintenance operations.

## Capabilities

### New Capabilities

- `platform/background-jobs`: the job queue, worker and supervisor processes, job lifecycle, API, progress, retries, cancellation, permission rechecks and limits.
- `platform/write-coordination`: write scopes and project write leases, conflict responses, the global write barrier, the active-writer registry and system leases.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.1: the `jobs`, `active_writers` and `system_leases` tables;
  - §9;
  - §13: Home recent jobs and job progress;
  - §14: `/jobs` routes, the 202 pattern, `RECORD_LOCKED`, `PROJECT_BUSY` and `MAINTENANCE_IN_PROGRESS`;
  - §16.3: steps 2 and 3, the barrier mechanism only;
  - §17: process termination;
  - §18.1: `worker` and `supervise`;
  - §19: group 10;
  - §20: M2 and the M7 backup-foundation note.
- **Depends on:** `m2-project-workspaces` and `m2-project-access-control`.
- **Code:** `src/litfoundry/jobs/`, the catalogue revision for `jobs` and `active_writers`, the CLI, and the frontend job components.
- **Later work:** job types are added by later changes (search, import, dedup, analysis, export, backup). The snapshot itself is in `m7-full-backup-and-restore`.
