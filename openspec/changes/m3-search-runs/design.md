# Design: M3 search runs

## Context

Compilation (`m3-search-strategy`), credentials and budgets (`m3-source-credentials`) and the job framework (M2) exist. This change defines how a search executes. The concrete OpenAlex and WoS Starter adapters arrive in their own changes.

## Goals / Non-Goals

**Goals:**
- One runner that executes any adapter, so the adapters stay small.
- Runs whose provenance can be reproduced from the stored raw pages alone.

**Non-Goals:**
- Canonical works, merging and provenance across sources (`m4-canonical-records`).
- File imports (`m3-source-file-imports`), which reuse the source-run records.

## Decisions

### Adapter protocol
The protocol is as in v1.3 §8:
- `capabilities()`
- `validate_credentials()`
- `compile()`
- `estimate()`
- `retrieve_page(query, credentials, cursor) -> SourcePage(records, raw_bytes, next_cursor, reported_count, cost_units, schema_version)`
- `normalize(raw_record)`

Adapters are registered by `source_id`. Fake adapters in `tests/fixtures/sources/` replay recorded pages and inject faults.

### HTTP client policy
- **Library:** `httpx` (BSD) with `verify=True` and explicit timeouts.
- **Allowed hosts:** a transport hook rejects any host not in the adapter's `ALLOWED_HOSTS` and allows no redirects to other hosts.
- **Credentials:** passed as request headers per call. The client is created per job, so headers are never shared between jobs.

### Runner
- **Scope:** the search job is an `append`-scope job.
- **Loop:** for each source run, the runner:
  1. resolves the credential;
  2. for each sub-query, loops over pages;
  3. calls `BudgetGuard.reserve`;
  4. calls `retrieve_page`;
  5. settles the budget;
  6. writes the raw page (write-once), then inserts `raw_records` and normalised rows inside `write_unit()`;
  7. saves `cursor_state`;
  8. calls `checkpoint()`.
- **Isolation:** each source run is processed independently. Its exception is caught, typed and recorded, and the search run's status is derived from all of them.
- **Resume:** after a reclaim, retrieval restarts from `source_runs.cursor_state`. Raw pages are keyed by `(source_run, sub_query, page_index)`, so re-inserting the same page is a no-op.

### Storage
- **Raw page path:** `sources/<search_run_uuid>/<source>/raw/<subquery>-<page>.json`.
- **`raw_records`:** each row points to its page file and holds the record's index and SHA-256.
- **Normalised records:** stored in `source_records(id, raw_record_id, provider, provider_record_id, normalized_json)`, which M4 consumes. This table is a helper not named in v1.3 §4.2 and is recorded in `docs/decisions.md`.

### Error mapping

| Adapter code | API code | Retryable |
|---|---|---|
| `AUTH_REQUIRED` | `SOURCE_ACCESS_DENIED` | no |
| `ACCESS_DENIED` | `SOURCE_ACCESS_DENIED` | no |
| `RATE_LIMITED` | `SOURCE_RATE_LIMITED` | yes |
| `SOURCE_UNAVAILABLE` | `SOURCE_UNAVAILABLE` (new) | yes |
| `PARTIAL_RESULTS` | `SOURCE_PARTIAL` | no |
| `INVALID_QUERY` | `VALIDATION_ERROR` | no |
| `UNSUPPORTED_FILTER` | `VALIDATION_ERROR` | no |

## Risks / Trade-offs

- [Large raw payload volume] → Pages are stored compressed (`.json.gz`), and per-project storage quotas apply (`m7-hardening`).
- [Duplicate inserts on resume] → Idempotent page keys, with a resume test.

## Migration Plan

Project revision adding `search_runs`, `source_runs`, `raw_records` and `source_records`.
