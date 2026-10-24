# Proposal: M3 search runs

## Why

A search must be reproducible and auditable. For every source, the system must record:
- what was asked;
- what the provider reported;
- what was actually retrieved;
- whether the retrieval was complete.

API counts are not evidence that every record was retrieved (v1.3 §8). Sources fail independently, and one failure must not discard the others' results. This change provides the common execution framework that the OpenAlex and WoS Starter adapters plug into.

## What Changes

- **Launch:** `POST /projects/{project_id}/search-runs` captures an immutable strategy version, compiles the strategy for the enabled API sources and starts a background search job. Disabled sources make zero calls.
- **Source run records:**
  - reported and retrieved counts;
  - completeness;
  - status and typed error code;
  - the executed request (without credentials);
  - credential scope;
  - checksum;
  - start and end times.
- **Raw payloads:** stored append-only and write-once under `sources/<search_run_uuid>/<source>/raw/`, with SHA-256, the provider's response schema version and the pagination state. Each record is also stored in its adapter-normalised form, ready for canonicalisation in M4.
- **Source adapter contract:**
  - typed error mapping;
  - bounded retries with backoff for retryable errors only;
  - outbound hosts restricted to an allowlist, with TLS verification;
  - credentials passed per request;
  - interrupted retrieval resumes from saved pagination state.
- **Search history:**
  - `/search-runs` lists runs and `/search-runs/{run_id}` shows status;
  - the Search history/results tab;
  - a test harness for source adapters.

## Capabilities

### New Capabilities

- `search/search-runs`: launching and recording searches, the source adapter contract, error typing, retries, outbound restrictions, completeness and search history.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `search_runs`, `source_runs` and `raw_records` tables;
  - §7.2: disabled providers make zero calls;
  - §8: the adapter interface, errors, SSRF rules, credentials per request and source-run fields;
  - §9: search jobs as an `append` scope;
  - §13: Search history/results;
  - §14: the `/search-runs` routes, `SOURCE_ACCESS_DENIED`, `SOURCE_RATE_LIMITED` and `SOURCE_PARTIAL`;
  - §17: outbound HTTP rules;
  - §19: group 6 (framework);
  - §20: M3.
- **Depends on:** `m3-search-strategy`, `m3-source-credentials` and `m2-background-jobs`.
- **Code:** `src/litfoundry/sources/` (adapter protocol, runner, HTTP client policy), the project migration revision, the API routes and the frontend history tab.
- **Followed by:** `m3-openalex-source` and `m3-wos-starter-source` (concrete adapters), and `m4-canonical-records` (canonical works).
