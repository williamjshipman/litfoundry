# Design: M7 hardening and release acceptance

## Context

Every v1 feature exists. This change adds cross-cutting limits, performance verification, documentation and the release acceptance run.

## Goals / Non-Goals

**Goals:**
- Quotas enforced at the few creation points that consume resources.
- A reproducible load test that runs in CI on demand and before every release.

**Non-Goals:**
- Personal-data export and pseudonymisation tools (MAY).
- Horizontal scaling.

## Decisions

### Quotas
- **Storage:** `Quotas` settings live in `system_settings`, with defaults in `config.py`.
- **Checks:** a `QuotaGuard` is called at project creation, upload, import, export and job submission (queued-jobs quota). Concurrent-job and worker limits are not quota checks: the job queue enforces them by leaving jobs queued (`m2-background-jobs`).
- **Usage counters:** per-project storage usage is maintained incrementally on file write and delete, and reconciled by housekeeping.
- **Default values:**

| Quota | Default |
|---|---|
| Projects per user | 50 |
| Storage per project | 20 GB |
| Upload size | 200 MB |
| Archive size | 5 GB |
| Queued jobs per user (refuses) | 20 |
| Concurrent jobs per user (queues) | 3 |
| Workers (queues) | 2 |

### Load testing
- **Tool:** Locust (MIT, test-only) in `tests/load/`.
- **Fixture:** a generated project with 10,000 source records and 8,000 works.
- **Users:** 5 viewers and 3 editors, while a search with a replay adapter and an analysis run.
- **Thresholds:** p95 under 2 s for Overview and record pages.
- **Scale check:** a separate 50,000-work fixture checks that pagination stays flat.

### Resilience tests
A chaos-style integration test kills the server and worker processes, using `SIGKILL` and `TerminateProcess`, during a search, an import, an analysis and a backup. It then runs `litfoundry reconcile` and asserts the invariants.

### Release acceptance
`tests/e2e/test_release_flow.py` covers the §19 group 12 scenario end to end:
1. bootstrap `admin`;
2. create local users and configure AD against the test directory;
3. pre-provision an AD user;
4. sign in as a local user and as an AD user;
5. create a project and search with fixture adapters;
6. deduplicate and screen;
7. produce the PRISMA SVG and run an analysis;
8. share the project;
9. export and import it;
10. sign out.

It runs with the CSP-violation collector, and it is executed against the packaged build on the clean Windows host.

## Risks / Trade-offs

- [CI runners differ from LAN servers] → Thresholds are evaluated on a documented reference machine before release. CI runs track regressions only.

## Migration Plan

Not applicable. Quota settings are seeded with defaults in `system_settings`.
