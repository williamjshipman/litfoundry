# Design: M3 source credentials and API budgets

## Context

Secret storage (M1) encrypts values. The job framework (M2) carries the requester's identity. This change adds credential records and metering, which the source adapters consume.

## Goals / Non-Goals

**Goals:**
- Credentials are resolved per job from the requester, and passed explicitly to adapters with each request. They are never stored in module-global library configuration (v1.3 §8).
- Metering is cheap enough to record on every call.

**Non-Goals:**
- Provider billing integration.
- Monetary accounting beyond the cost units each provider reports.

## Decisions

### Data
- **`source_credentials`:** holds `id`, `scope` (`global` or `user`), `user_id`, `provider`, `secret_ref`, `enabled`, `budget_daily`, `per_user_cap_daily` (shared only), `validation_status`, `validated_at` and `updated_at`.
- **Secret reference:** `secret_ref` points to an encrypted secret row.
- **`api_usage`:** holds `credential_id`, `day_utc`, `user_id`, `provider`, `calls` and `cost_units`. The unique key `(credential_id, day_utc, user_id)` allows upserts, and remaining budget is a sum over it.

### Resolution
- **Function:** `resolve_credential(requester_id, provider) -> EffectiveCredential(scope, credential_id, secret)`.
- **When it is called:** when the job starts. The secret is held only in job memory and is never placed in `jobs.args_json`.

### Budget enforcement
- **Reservation:** `BudgetGuard.reserve(credential, user, estimated_units)` runs before each call, followed by `settle(actual_units)` from the response header.
- **Atomicity:** both run in a short catalogue transaction. `api_usage` is an operational table, so these writes are exempt from the write barrier: metering continues while jobs buffer retrieval.
- **Cost units:**
  - OpenAlex: one unit is $0.0001 of the reported cost, read from `X-RateLimit-Credits-Used`.
  - WoS Starter: one unit is one request.
- **Default budgets** (configurable in Admin → API keys):
  - OpenAlex: the free $1 per day;
  - WoS Starter: the plan quota, chosen at configuration.

### Validation calls
- **OpenAlex:** a single `per-page=1` filter request.
- **WoS Starter:** a `limit=1` query.

Validation calls are metered like any other call.

## Risks / Trade-offs

- [The OpenAlex cost header changes name or units] → It is isolated in the OpenAlex adapter's `cost_from_response()`. v1.3 A.3 requires checking current terms before release.
- [`api_usage` is added to the barrier-exempt list, which v1.3 §16.3 did not name] → Recorded in `docs/decisions.md`. The table holds only metering counters.

## Migration Plan

Catalogue revision adding `source_credentials` and `api_usage`.
