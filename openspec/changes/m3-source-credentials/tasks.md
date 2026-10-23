# Tasks: M3 source credentials and API budgets

## 1. Credentials

- [ ] 1.1 Add the catalogue revision for `source_credentials` and `api_usage`. Verify with migration tests.
- [ ] 1.2 Implement `GET`/`PUT /api/v1/admin/source-credentials/{provider}` and `GET`/`PUT /api/v1/me/source-credentials/{provider}`, with write-only encrypted secrets and admin-only access to shared credentials. Verify with API tests and the secret-leak scan.
- [ ] 1.3 Implement `resolve_credential` precedence (personal, then shared, then none), never using another user's personal credential. Verify with unit tests, including a job launched by the admin in a user's project.
- [ ] 1.4 Implement credential validation through the adapter `validate_credentials()` interface, with stored status. Verify with a fake adapter test.
- [ ] 1.5 Record the credential scope on source runs, which are created in `m3-search-runs`. Verify with a unit test of the resolution output.

## 2. Budgets

- [ ] 2.1 Implement `BudgetGuard` (reserve and settle, daily UTC reset, per-user caps on shared keys) as a barrier-exempt operational write. Verify with unit tests for exhaustion, caps and the midnight reset (§19 group 6).
- [ ] 2.2 Return `SOURCE_BUDGET_EXCEEDED` with partial results kept, and require confirmation when an estimate exceeds the remaining budget. Verify with job tests using a fake adapter.
- [ ] 2.3 Add `api_usage` to the documented barrier-exempt list in `docs/architecture.md` and `docs/decisions.md`. Verify with a barrier test that metering continues.

## 3. GUI

- [ ] 3.1 Build Admin → API keys (shared keys, validation, budgets, per-user caps, usage for all keys). Verify with a Playwright test.
- [ ] 3.2 Build the personal API-key settings (set, enable, remove, usage, remaining cap) and the credential-origin indicator in the search editor. Verify with a Playwright test.
