# Proposal: M3 source credentials and API budgets

## Why

Bibliographic APIs need keys. The administrator provides shared keys, and users may supply their own (v1.3 decision 5, §5.6). OpenAlex is metered in dollars per day, and WoS Starter has daily request quotas. Without per-key budgets, one user's search could exhaust a shared key for everyone (v1.3 §8). A job must never use another user's personal key.

## What Changes

- **Shared credentials:** each source has an admin-managed shared credential (`/admin/source-credentials/{provider}`). Secrets are write-only and validated, and status and usage are shown.
- **Personal credentials:** each user can set a personal override (`/me/source-credentials/{provider}`).
- **Precedence:** the job requester's enabled personal credential, then the enabled shared credential, then none. Another user's personal credential is never used, including when the admin runs the job.
- **Provenance:** source runs record which credential scope was used, and never the secret.
- **Usage recording:** each call is recorded per key:
  - OpenAlex: cost read from `X-RateLimit-Credits-Used`;
  - WoS Starter: request count.
- **Budgets:**
  - configurable daily budgets per key, with an optional per-user cap on shared keys;
  - `SOURCE_BUDGET_EXCEEDED` keeps the partial results;
  - a warning before a run whose estimate exceeds the remaining budget.

## Capabilities

### New Capabilities

- `search/source-credentials`: shared and personal source credentials, precedence, validation, display and provenance.
- `search/api-budgets`: per-key usage recording, daily budgets, the per-user cap on shared keys and the usage views.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §1: decision 5;
  - §4.1: the `source_credentials` table;
  - §5.6;
  - §8: the OpenAlex and WoS budget paragraphs;
  - §13: Admin shared API keys, status and usage;
  - §14: the source-credentials routes and `SOURCE_BUDGET_EXCEEDED`;
  - §17: the credential bullets;
  - §19: group 6 (quota and budget);
  - §20: M3.
- **Depends on:** `m1-platform-foundation` (secret storage), `m1-local-identity` and `m2-background-jobs`.
- **Code:** `src/litfoundry/sources/credentials.py` and `budgets.py`, the catalogue revision, the API routes, Admin → API keys and the personal settings screen.
