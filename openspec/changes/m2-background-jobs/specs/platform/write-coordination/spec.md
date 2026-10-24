# Spec Delta: platform/write-coordination

## Purpose

Coordinates every writer to the catalogue and project databases, so background jobs, interactive edits and maintenance operations never corrupt or block each other unnecessarily.

## ADDED Requirements

### Requirement: Job write scopes
Every job that writes to a project SHALL declare one of three write scopes:

| Scope | What the job writes | Example |
|---|---|---|
| `append` | new rows only | a search import |
| `records` | a listed set of work IDs | a merge or bulk screening update |
| `project` | the whole project | a migration |

#### Scenario: Scope recorded
- **WHEN** a deduplication merge job is enqueued
- **THEN** its recorded scope is `records`, with the affected work IDs

### Requirement: Project write lease
At most one `records` or `project` job SHALL hold a project's write lease at a time. `append` jobs SHALL be able to run alongside it.

#### Scenario: Import during merge
- **WHEN** a merge job holds the write lease and a search import starts
- **THEN** the import runs concurrently

#### Scenario: Two records jobs
- **WHEN** a second `records` job is ready while one holds the lease
- **THEN** the second waits in `queued`

### Requirement: Interactive edits during jobs
Interactive single-record edits SHALL NOT take the write lease; they SHALL use short transactions and optimistic concurrency. An edit that touches a work held by a running `records` job SHALL be refused with 409 `RECORD_LOCKED`. Any interactive edit during a `project` job SHALL be refused with 409 `PROJECT_BUSY`.

#### Scenario: Edit locked record
- **WHEN** a reviewer edits a work that a running merge job holds
- **THEN** the response is 409 `RECORD_LOCKED`

#### Scenario: Edit unrelated record
- **WHEN** a reviewer edits a work not held by the running merge job
- **THEN** the edit succeeds

### Requirement: Global write barrier
A maintenance operation SHALL be able to raise a global write barrier, which moves from `draining` to `frozen`. While it is raised:
- new application-data write units SHALL wait briefly and then fail with 503 `MAINTENANCE_IN_PROGRESS` and `Retry-After`;
- background jobs SHALL pause at their next write checkpoint and resume after release.

Network retrieval can continue, buffered to the job's temp area up to a limit.

#### Scenario: Edit during barrier
- **WHEN** a user saves a record while the barrier is frozen
- **THEN** the response is 503 `MAINTENANCE_IN_PROGRESS` with `Retry-After`

#### Scenario: Job pauses and resumes
- **WHEN** the barrier is raised while a search job is importing
- **THEN** the job pauses at its next write checkpoint and resumes after the barrier is released

### Requirement: Active writer registry
Every application-data write unit SHALL register as an active writer while it runs. The barrier SHALL become `frozen` only when no active writers remain. If draining exceeds the configured timeout, the maintenance operation SHALL fail safely and release the barrier.

#### Scenario: Drain timeout
- **WHEN** an active writer does not finish within the drain timeout
- **THEN** the maintenance operation fails and normal writes resume

### Requirement: Exempt operational writes
These operational writes SHALL remain allowed while the barrier is raised, so sign-in, token refresh, job heartbeats and audit entries keep working:
- job lease, heartbeat and progress fields;
- refresh tokens;
- login throttling;
- system audit events;
- last-sign-in times;
- system leases;
- the active-writer registry;
- backup run records.

#### Scenario: Token refresh during barrier
- **WHEN** a session refreshes its token while the barrier is frozen
- **THEN** the refresh succeeds

### Requirement: Exclusive system leases
Maintenance operations (migration, full backup, full restore and the scheduler) SHALL be coordinated through named, expiring, fenced system leases, so conflicting operations never run at the same time. A lease whose holder has died SHALL expire and be reclaimable.

#### Scenario: Stale lease
- **WHEN** a process holding the maintenance lease dies
- **THEN** after expiry another operation can acquire the lease, with a higher fencing token
