# Tasks: M3 search runs

## 1. Framework

- [ ] 1.1 Add the project revision for `search_runs`, `source_runs`, `raw_records` and `source_records`. Verify with migration tests.
- [ ] 1.2 Define the `SourceAdapter` protocol and `SourcePage` types, and build the fake replay and fault-injection adapters. Verify with unit tests.
- [ ] 1.3 Implement the outbound HTTP client policy (allowlisted hosts, TLS verification, timeouts, no cross-host redirects, per-job headers). Verify with tests that a disallowed host or redirect is refused.
- [ ] 1.4 Implement the error mapping and bounded retry with `Retry-After`. Verify with fault-injection tests.

## 2. Runner

- [ ] 2.1 Implement the search job runner (`append` scope, budget reserve and settle, write-once raw pages, raw and normalised rows, cursor checkpoints, per-source isolation). Verify with fake-adapter tests for success, auth failure, partial, budget exhaustion and one source failing (§19 group 6).
- [ ] 2.2 Implement resume from `cursor_state` with idempotent page keys. Verify with a kill-and-reclaim test that asserts no duplicate records.
- [ ] 2.3 Implement the completeness rules and `missing_required_fields_count`. Verify with fixtures for a paging limit and missing abstracts.
- [ ] 2.4 Verify per-request credentials with two concurrent jobs using different keys in one worker. Verify that each request carries its own job's key.
- [ ] 2.5 Assert that disabled sources produce zero calls across preview, search and enrichment paths. Verify with a request-recording transport (§19 group 5).

## 3. API and GUI

- [ ] 3.1 Implement `POST`/`GET /api/v1/projects/{project_id}/search-runs` and `GET .../search-runs/{run_id}`, with the edit permission for launch and the budget confirmation flow. Verify with API tests.
- [ ] 3.2 Build the Search history/results tab (runs, per-source counts, completeness, errors, query versions, retry). Verify with a Playwright test using fixture adapters.
- [ ] 3.3 Document the search-run provenance model in `docs/data-model.md`. Verify that every source-run field is described.
