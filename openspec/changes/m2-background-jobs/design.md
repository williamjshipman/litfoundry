# Design: M2 background jobs

## Context

Projects and authorisation exist. This change adds the execution model that every long-running feature uses, and the coordination primitives that M7's consistent full backup depends on. The `system_leases` table was created in `m2-project-workspaces`.

## Goals / Non-Goals

**Goals:**
- No external broker. The queue lives in `catalog.sqlite`, so idle workers can find work without scanning project databases.
- Barrier and write-scope behaviour testable without a real backup.

**Non-Goals:**
- Distributed workers on other hosts. Only the server host runs workers, because it owns the SQLite files.
- Scheduled backups (`post-v1-scheduled-backups`).

## Decisions

### Queue
- **Claiming:** `jobs` rows are claimed with `UPDATE ... SET lease_owner=?, lease_expires_at=? WHERE id=(SELECT id FROM jobs WHERE status='queued' AND not_before<=now ORDER BY priority, created_at LIMIT 1) AND lease_owner IS NULL`. This is a single statement and safe under SQLite's database-level write lock.
- **Leases:** a heartbeat thread renews the lease every 10 s, and leases last 60 s.
- **Reclaim:** on start, a worker reclaims expired leases (`attempt+1`, back to `queued`, or `failed` once `max_attempts` is reached).
- **Handlers:** registered by `type`. Each receives a `JobContext` with `checkpoint()`, `progress()`, `authorize()`, `write_unit()` and a project temp directory.
- **Checkpoints:** `ctx.checkpoint()` handles cancellation (raises `JobCancelled`), the barrier (blocks while it is raised) and the lease. Handlers call it between batches and inside `write_unit()`.

### Write units
- **Interface:** `with write_unit(operation, project_id):` registers a row in `active_writers`, checks the barrier and opens a short transaction.
- **Web side:** mutating API routes are wrapped by a decorator that does the same. The barrier wait is up to 2 s before returning 503.
- **Exempt writes:** the tables listed in the spec use a separate `operational_session()` that bypasses the barrier check, so the exemption is explicit in code.

### Barrier state
- **Storage:** the `write-barrier` row in `system_leases`, holding `state` (`draining`, `frozen` or `released`), `owner`, `fencing_token` and an expiry.
- **Reads:** every process reads it at each write unit, with a cached read of at most 250 ms.

### Write scopes
- **Storage:** `jobs.scope_json` holds `{"scope": "records", "work_ids": [...]}`.
- **Lease:** the per-project write lease is a `system_leases` row named `project-write:<uuid>`.
- **Conflict checks:** `RECORD_LOCKED` is detected by intersecting the edited work ID with the `work_ids` of running `records` jobs for the project. For large ID sets, the check uses a `job_locked_works(job_id, work_id)` helper table indexed by `work_id`.

### Supervisor
- **Implementation:** `litfoundry supervise` uses `subprocess` to run `litfoundry-server` and N × `litfoundry-worker`. Crashed children restart with backoff, and shutdown forwards SIGTERM or CTRL_BREAK.
- **Use:** it is the single entry point for the OS service in M7.

### Idempotency
Clients send an `Idempotency-Key` header. It is stored in `jobs.idempotency_key` (unique) and scoped as `<requester>:<key>`.

## Risks / Trade-offs

- [SQLite write contention on `jobs`] → Heartbeats are small single-row updates with a busy timeout. The worker count is small (LAN scale).
- [Barrier pauses jobs too long] → The barrier holds only during the database snapshot step (v1.3 §16.3 step 3), and network retrieval continues.
- [Exempt-write bypass misused] → `operational_session()` is restricted to an allowlist of tables, with a unit test.

## Migration Plan

Catalogue revision adding `jobs`, `active_writers` and `job_locked_works`.
