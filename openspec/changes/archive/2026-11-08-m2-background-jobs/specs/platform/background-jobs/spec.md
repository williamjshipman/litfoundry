# Spec Delta: platform/background-jobs

## Purpose

Runs long operations reliably outside web requests, with visible progress, safe cancellation, recovery after crashes and fair resource limits.

## ADDED Requirements

### Requirement: Separate worker process
Long-running operations SHALL run in a worker process started with `litfoundry worker`, never in web request threads. No bibliographic API call SHALL block a web request thread.

#### Scenario: Search does not block requests
- **WHEN** a search job is running
- **THEN** other API requests are answered normally by the server process

### Requirement: Supervisor
`litfoundry supervise` SHALL start the server and the configured number of worker processes. It SHALL restart a child that exits unexpectedly and stop all children on shutdown.

#### Scenario: Worker crash
- **WHEN** a worker process is killed
- **THEN** the supervisor starts a replacement worker

### Requirement: Asynchronous operation pattern
Endpoints that start long operations SHALL respond 202 Accepted with `job_id`, `status` and a `links.status` URL, without waiting for the work.

#### Scenario: Start an operation
- **WHEN** a client starts a long operation
- **THEN** the response is 202 with a job ID whose status can be polled

### Requirement: Job states
Jobs SHALL have one of these states:
- `queued`
- `running`
- `partial`
- `completed`
- `failed`
- `cancelling`
- `cancelled`

Each job SHALL record its requester, project, type, structured progress, correlation ID, attempt count and last error code.

#### Scenario: Partial outcome
- **WHEN** a job finishes with some sub-tasks failed and others succeeded
- **THEN** its state is `partial` and its progress lists which parts failed

### Requirement: Job status API
- `GET /api/v1/jobs/{job_id}` SHALL return a job's state, progress and a log summary to its requester, to users with read access to its project, and to the administrator.
- `GET /api/v1/jobs` SHALL return the caller's recent jobs; for the administrator, it SHALL return all jobs.

#### Scenario: Another user's job
- **WHEN** a user without access to the job's project requests the job
- **THEN** the response is 404

### Requirement: Failed job reporting
A job in state `failed` SHALL report error code `JOB_FAILED` in its status, together with the typed cause (for example `SOURCE_ACCESS_DENIED` or `FORBIDDEN`) and a redacted message. Endpoints that return a failed job's results SHALL respond with `JOB_FAILED`.

#### Scenario: Results of a failed job
- **WHEN** a client requests the results of an analysis whose job failed
- **THEN** the response carries code `JOB_FAILED` and the typed cause

### Requirement: Leases and recovery
A running job SHALL hold an expiring lease that is renewed by heartbeat. On worker start and on lease expiry, jobs SHALL be reclaimed and retried idempotently up to their maximum attempts, then marked `failed`. A job SHALL never be reported `completed` unless its work was committed.

#### Scenario: Worker killed mid-job
- **WHEN** the worker running a job is killed and its lease expires
- **THEN** another worker resumes or retries the job, and the job is not marked completed until its results are committed

### Requirement: Idempotent submission
A client-supplied idempotency key SHALL make repeated submissions of the same operation return the existing job instead of creating another.

#### Scenario: Double submit
- **WHEN** a client submits the same operation twice with the same idempotency key
- **THEN** both responses carry the same job ID

### Requirement: Bounded retries
Jobs SHALL retry only failures classified as retryable, with exponential backoff and a bounded number of attempts. Other failures SHALL fail the job immediately with a typed error code.

#### Scenario: Non-retryable failure
- **WHEN** a job fails with an invalid-query error
- **THEN** it is marked `failed` without retrying

### Requirement: Cancellation at checkpoints
`POST /api/v1/jobs/{job_id}/cancel` SHALL be idempotent. It SHALL move a queued job to `cancelled`, and a running job to `cancelling` and then `cancelled` at its next checkpoint. An open database transaction SHALL never be interrupted.

#### Scenario: Cancel running job
- **WHEN** the requester cancels a running import
- **THEN** the job stops at its next checkpoint, its state becomes `cancelled` and the project database passes an integrity check

#### Scenario: Repeat cancel
- **WHEN** cancel is called twice on the same job
- **THEN** both calls succeed and the job is cancelled once

### Requirement: Permission recheck
A job SHALL recheck its requester's permission before it starts and before each time it persists results. If the permission is gone, it SHALL stop without persisting and record a `FORBIDDEN` failure.

#### Scenario: Revoked before persist
- **WHEN** the requester loses edit access while their job is running
- **THEN** the job stops before its next write and records a permission failure

### Requirement: Concurrency limits
The system SHALL enforce configurable per-user and global limits on concurrently running jobs. Jobs above a limit SHALL stay queued until capacity frees.

#### Scenario: Per-user limit
- **WHEN** a user with a limit of two running jobs starts a third
- **THEN** the third stays `queued` until one of the first two finishes

### Requirement: Job progress in the GUI
The GUI SHALL show job state and progress, polling every 2–5 seconds while the page is visible and less often in background tabs. The Home page SHALL list the user's recent jobs.

#### Scenario: Progress updates
- **WHEN** a user watches a running job
- **THEN** its progress updates without a page reload

### Requirement: Job queue health
The readiness endpoint, `litfoundry status` and the admin system screen SHALL report queued, running and failed job counts and the last heartbeat of each worker.

#### Scenario: No worker running
- **WHEN** no worker has sent a heartbeat within the lease period
- **THEN** readiness reports the worker check as failed
