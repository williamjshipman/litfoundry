# LitFoundry Architecture

## Overview

LitFoundry is a Python/Flask application for systematic literature reviews with a Vue 3 front-end. It uses a central SQLite catalogue database and per-project SQLite databases. Long-running operations execute in separate worker processes coordinated through the catalogue queue.

## System Architecture

### Components

1. **Server Process** (`litfoundry serve`)
   - Flask application bound to `127.0.0.1:5080`
   - Handles web API requests and serves the frontend
   - Behind a Caddy TLS reverse proxy in production
   - Single process (no clustering)

2. **Worker Processes** (`litfoundry worker`)
   - Run long-executing jobs from the queue
   - Multiple workers run in parallel (typically 2-4)
   - Managed by supervisor process in production
   - Auto-restart on crash with exponential backoff

3. **Supervisor** (`litfoundry supervise --workers N`)
   - Manages server and N worker subprocesses
   - Restarts crashed children with backoff
   - Graceful shutdown (30s timeout for children)
   - Single entry point for the systemd service

4. **Catalogue Database** (`catalog.sqlite`)
   - Central SQLite database in WAL mode
   - Stores: users, projects, ACLs, jobs, leases, audit events, system settings
   - Schema versioned with Alembic (run via Flask-Alembic migrations)

5. **Project Databases** (`projects/<uuid>/project.sqlite`)
   - One per project, isolated data
   - Stores: records, screening decisions, analyses, snapshots
   - Schema versioned with Alembic programmatic API

## Background Job System

### Job Queue Model

Jobs are stored in the `jobs` table in the catalogue database:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Unique job identifier |
| `type` | String | Job type (e.g., "import", "merge", "migration") |
| `user_id` | UUID | User who requested the job (None for system jobs) |
| `project_id` | UUID | Project the job operates on (None for system jobs) |
| `status` | Enum | One of: queued, running, partial, completed, failed, cancelling, cancelled |
| `priority` | Int | 0-100, higher priority claimed first |
| `attempt` | Int | Retry attempt number (1-based) |
| `max_attempts` | Int | Maximum retries allowed (default 3) |
| `scope_json` | JSON | Write scope: `{"scope": "append\|records\|project", "work_ids": [...]}` |
| `progress_json` | JSON | Structured progress: `{"message": "...", "percent_complete": 0.5, ...}` |
| `error_code` | String | Last error code ("JOB_FAILED", "SOURCE_ACCESS_DENIED", etc.) |
| `error_message` | String | Last error message (redacted) |
| `error_cause` | String | Typed error cause (for classification) |
| `lease_owner` | UUID | Worker ID holding the job's lease (None if queued) |
| `lease_expires_at` | Timestamp | When lease expires (60 seconds from heartbeat) |
| `correlation_id` | UUID | Trace ID for logging and debugging |
| `idempotency_key` | String | Client key for deduplication (unique per user) |
| `not_before` | Timestamp | Earliest time job can be claimed |
| `created_at` | Timestamp | When job was enqueued |
| `started_at` | Timestamp | When job transitioned to running |
| `completed_at` | Timestamp | When job reached terminal state |

### Job States and Transitions

```
                         ┌─────────────────────────────────┐
                         │        QUEUED                   │
                         │ (waiting to be claimed)         │
                         └──────────┬──────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌────────────┐   ┌───────────┐  ┌──────────────┐
            │   RUNNING  │   │ CANCELLED │  │    FAILED    │
            │ (executing)│   │ (by user) │  │ (max retries)│
            └────┬───────┘   └───────────┘  └──────────────┘
                 │
        ┌────────┼────────────┐
        │        │            │
        ▼        ▼            ▼
   ┌─────────┬──────────┬──────────────┐
   │COMPLETED│ PARTIAL  │  CANCELLING  │
   │(success)│(some fail)│(pausing...  │
   └─────────┴──────────┴──────────────┘
                        │
                        ▼
                   ┌──────────────┐
                   │  CANCELLED   │
                   └──────────────┘
```

**Transitions:**
- `queued → running`: Worker claims job atomically
- `running → completed`: All tasks succeeded
- `running → partial`: Some tasks failed, some succeeded
- `running → failed`: Non-retryable error or max retries exhausted
- `running → cancelling`: User requests cancellation
- `cancelling → cancelled`: At next checkpoint
- `queued → cancelled`: Cancelled before it started
- `queued → running → queued`: Lease expires, job retried (if `attempt < max_attempts`)
- `queued → running → failed`: Lease expires (if `attempt >= max_attempts`)

**Terminal states:** `completed`, `partial`, `failed`, `cancelled`

### Lease and Heartbeat

- **Claiming:** Atomic `UPDATE ... SET lease_owner, status='running'` where `lease_owner IS NULL`
- **Lease Duration:** 60 seconds
- **Heartbeat:** Worker renews lease every 10 seconds (separate daemon thread)
- **Expiry:** Unclaimed leases (stale workers) auto-reclaimed on next `claim()` call
- **Retry:** Expired jobs increment attempt, move back to `queued` (if retryable), or `failed` (if max attempts reached)

### Job Concurrency Limits

- **Global limit:** `MAX_RUNNING_JOBS_GLOBAL = 20` jobs across all users
- **Per-user limit:** `MAX_RUNNING_JOBS_PER_USER = 5` jobs per user
- **Enforcement:** Checked at claim time, not at enqueue
- **Result:** Jobs above limits stay `queued` until capacity frees

### Idempotency

- **Key scope:** Per-user (same user + same key = same job)
- **Storage:** `jobs.idempotency_key` (unique constraint on `(user_id, idempotency_key)`)
- **Semantics:** Repeated submissions with same key return the existing job ID
- **Use case:** API clients that retry failed requests

### Error Classification

**Retryable Errors** (use `RetryableError`):
- Transient network errors
- Temporary database locks
- Resource exhaustion (retry with backoff)

**Non-Retryable Errors** (use `NonRetryableError`):
- Invalid parameters (`error_cause="VALIDATION_ERROR"`)
- Permission denied (`error_cause="FORBIDDEN"`)
- Not found (`error_cause="SOURCE_NOT_FOUND"`)
- Max retries reached (`error_code="JOB_FAILED"`)

**Redacted Error Messages:**
- User-facing messages avoid internal stack traces
- Log full details separately for debugging

## Write Coordination System

### Problem Statement

Multiple writers (background jobs, interactive edits, maintenance operations) must coordinate to prevent:
1. Lost updates (edits during job)
2. Phantom successes (incomplete commits)
3. Data corruption (concurrent incompatible operations)

### Write Scopes

Jobs declare their write scope in `jobs.scope_json`:

| Scope | What's Written | Example | Can run with |
|-------|---------------|---------|--------------|
| `append` | New rows only | Search import | Other append, records, project jobs |
| `records` | Listed work IDs | Merge, bulk screening | Other append jobs (queued if records/project running) |
| `project` | Whole project | Migration, full export | Only other append jobs (queued if any records/project running) |

### Per-Project Write Lease

- **Stored:** System lease named `project-write:<uuid>`
- **Held by:** At most one active `records` or `project` job
- **Exclusive:** Only one can run; others queue
- **Append jobs:** Exempt, can run alongside
- **Interactive writes:** Use optimistic locking, not leases

### Interactive Edit Checks

When user edits a record:

1. If a `records` job is running and affected record is locked: **409 RECORD_LOCKED**
2. If a `project` job is running (any edit): **409 PROJECT_BUSY**
3. Otherwise: Use short transaction, optimistic version check

### Global Write Barrier

Used by maintenance operations (migration, full backup, restore) to pause all writes temporarily.

**States:**
- **Released:** Normal operations, no restrictions
- **Draining:** Active writers still running, new writes can proceed
- **Frozen:** No active writers, new writes rejected with **503 MAINTENANCE_IN_PROGRESS**

**Storage:** System lease named `write-barrier` with fields:
- `state`: Current state
- `owner`: Maintenance operation ID
- `fencing_token`: For stale operation detection
- `expires_at`: Lease expiry time

**Barrier Lifecycle:**

```
released → (maintenance op acquires lease, raises barrier) → draining
         ↓ (active writers drain within timeout)
       frozen → (maintenance work completes) → released
```

**Writer Behavior:**

| State | Interactive Write | Job Write Unit | Job Checkpoint |
|-------|------------------|-----------------|-----------------|
| Released | OK (short txn) | OK | OK |
| Draining | Wait 2s then 503 | Wait 2s then 503 | Wait indefinitely |
| Frozen | 503 + Retry-After | 503 + Retry-After | Wait indefinitely |

**Drain Timeout:** Configurable (default 120s). If timeout reached while draining, maintenance op fails safely and releases barrier.

**Caching:** Barrier state cached for 250ms per writer to reduce database load.

### Active Writer Registry

Stored in `active_writers` table:

| Field | Purpose |
|-------|---------|
| `id` | Registration ID (UUID) |
| `job_id` | Job performing write (NULL for interactive) |
| `project_id` | Project being written |
| `scope_json` | Write scope details (for validation) |
| `registered_at` | When registered |
| `expires_at` | Lease expiry (10 minutes) |

**Registration:** Each write unit (job or interactive) registers before opening transaction
**Unregistration:** Automatically on context exit
**Cleanup:** Expired rows cleaned by barrier freeze logic

### Exempt Operational Writes

These operations bypass barrier checks to keep the system responsive:

| Table | Purpose | Why Exempt |
|-------|---------|-----------|
| `job_leases` | Job lease/heartbeat | Workers must keep system alive |
| `job_progress` | Job progress updates | User-visible updates |
| `refresh_tokens` | Session token refresh | Users can't log in otherwise |
| `login_throttle` | Login rate limits | Can't lock out users |
| `audit_events` | Admin audit trail | Audit must not fail |
| `last_sign_in` | Login timestamps | Operational tracking |
| `system_leases` | Maintenance coordination | Coordination must succeed |
| `active_writers` | Barrier registration | Barrier control depends on it |
| `backup_run_records` | Backup tracking | Backup orchestration |

**Implementation:** Use `operational_session()` context instead of `write_unit()`:
```python
with coordinator.operational_session(session):
    session.execute(...)  # Bypasses barrier check
```

### Fenced System Leases

Maintenance operations (migration, full backup, restore, scheduler) coordinate through exclusive system leases.

**Storage:** `system_leases` table with fields:
- `name`: Lease name (e.g., "migration", "full-backup")
- `owner`: Owner ID (process/worker that holds it)
- `fencing_token`: Incrementing token (detects stale operations)
- `state`: Lease state (`released` or held with barrier state)
- `expires_at`: Lease expiry timestamp

**Lease Lifecycle:**

1. **Acquire:** Check if lease is held (not expired), increment fencing token on reclaim
2. **Hold:** Owner runs operation with fencing token
3. **Release:** Only owner with matching fencing token can release
4. **Stale Detection:** If owner dies, lease expires and can be reclaimed with higher token

**Semantics:**
- **Exclusive:** Only one operation holds a named lease at a time
- **Expiring:** Lease has timeout (default 300s for operations)
- **Fenced:** Stale operations (owner crashed) can't corrupt data because token mismatches on release

## Request/Job Flow

### Enqueue a Job (Interactive Request)

```
1. User submits form (e.g., import search)
2. Browser POST /api/v1/jobs
3. API endpoint:
   - Check user permission
   - Validate idempotency key (dedup if needed)
   - Call queue.enqueue() → returns job_id
   - Return 202 Accepted with job_id
4. Browser polls GET /api/v1/jobs/{job_id} for status
```

### Claim and Execute Job (Worker)

```
1. Worker: claim() → atomic SELECT+UPDATE for next queued job
2. Worker: register handler and execute in JobContext
3. Job handler:
   - Calls ctx.authorize() to check permission
   - Calls ctx.checkpoint() at batch boundaries (checks cancellation, barrier, renews lease)
   - Calls ctx.write_unit() to register writes and check barriers
   - Updates progress with ctx.progress()
4. On success: mark_completed()
5. On error:
   - If retryable: mark_failed(..., is_retryable=True) → job moves back to queued
   - If non-retryable: mark_failed(..., is_retryable=False) → job marked failed
   - If cancelled: mark_cancelled()
6. Heartbeat thread keeps renewing lease every 10s
```

### Permission Recheck

Jobs recheck permissions:
- **Before start:** `ctx.authorize()` called by execute_job()
- **Before persist:** Caller responsible to recheck in write unit
- **On permission lost:** Job fails with `error_code="JOB_FAILED"`, `error_cause="FORBIDDEN"`

## Database Schemas

### Key Tables

**jobs** (catalogue)
- Job queue, leases, progress, errors

**active_writers** (catalogue)
- Active write units (jobs and interactive edits)

**job_locked_works** (catalogue)
- Indexed map of which job holds which work ID (for RECORD_LOCKED checks)

**system_leases** (catalogue)
- Maintenance operation coordination (barrier, migration, backup, scheduler)

**users** (catalogue)
- User accounts, roles, active status

**project_acl** (catalogue)
- Per-project user permissions (viewer, editor)

**audit_events** (catalogue)
- Admin action history

**project_directory** (catalogue)
- Project metadata, path, owner

**records**, **decisions**, **analyses** (per-project database)
- Screening records and their data

## API Endpoints

### Job Status

- `GET /api/v1/jobs` - List user's jobs (admin sees all)
- `GET /api/v1/jobs/{job_id}` - Get job state, progress, errors
- `POST /api/v1/jobs/{job_id}/cancel` - Cancel running or queued job (idempotent)

**Responses:**
- 200 OK: Job details
- 202 Accepted: Job created/cancelled (async operation)
- 404 Not Found: Job not accessible
- 403 Forbidden: Permission denied

### Admin Endpoints

- `GET /api/v1/jobs/queue/health` - Queue statistics (admin only)
  - Returns: queued_count, running_count, failed_count, worker_heartbeats
- `GET /api/v1/health/ready` - Readiness check including queue health (admin only)
  - Returns: status, checks (including job_queue check)

### CLI Commands

- `litfoundry worker` - Start a worker process
- `litfoundry supervise --workers N` - Start server + N workers with management
- `litfoundry status` - Check system health including queue status
- `litfoundry migrate` - Run catalogue and project database migrations (uses system lease)

## Error Codes

### Job-Related

- `JOB_FAILED` - Job failed (status when error_cause is set)
- `JOB_NOT_FOUND` - Job doesn't exist or user doesn't have access
- `FORBIDDEN` - User lost permission while job was running

### Write Coordination

- `RECORD_LOCKED` - 409: Record is locked by running records job
- `PROJECT_BUSY` - 409: Project has running project-scope job
- `MAINTENANCE_IN_PROGRESS` - 503: Write barrier is frozen, retry after 2s

### Job Errors (Typed Causes)

- `SOURCE_ACCESS_DENIED` - Can't access bibliographic API
- `VALIDATION_ERROR` - Invalid parameters
- `SOURCE_NOT_FOUND` - Source not configured
- `HANDLER_NOT_FOUND` - No handler for job type
- `LEASE_EXPIRED` - Lease expired after max retries
- `INTERNAL_ERROR` - Unexpected exception

## Performance Considerations

1. **Lease Contention:** 60-second leases with 10-second heartbeats minimize SQLite write contention
2. **Barrier Caching:** 250ms cache of barrier state reduces repeated database reads
3. **Concurrency Limits:** Prevent resource exhaustion (global and per-user)
4. **Optimistic Locking:** Interactive edits use short transactions, not long-held leases
5. **Batching:** Checkpoint every N items to prevent long transaction hold times
6. **Async Polling:** Clients poll job status at 2-5s intervals (Page Visibility API for slower background updates)

## Testing Strategy

- **Unit tests:** State machine transitions, lease logic, barrier behavior
- **Integration tests:** Full workflow from enqueue to completion
- **Concurrency tests:** Concurrent job claims, concurrent edits, barrier draining
- **Failure tests:** Worker crash recovery, permission revocation, lease expiry, cancellation at checkpoint
- **Load tests:** Global and per-user limits, queue throughput

## Future Extensions

- **Scheduled jobs:** Use system leases to coordinate scheduler
- **Job dependencies:** Allow jobs to wait for other jobs
- **Bulk operations:** Transactional bulk write operations
- **Job webhooks:** Notify external systems when job completes
- **Distributed workers:** Future multi-host deployment (post-v1)
