# Design: M1 local identity

## Context

The catalogue and secret storage (`m1-platform-foundation`) and the API contract and SPA shell (`m1-web-foundation`) exist. This change adds the identity tables and flows. Its provider abstraction must accept the Active Directory provider in M2 without rework.

## Goals / Non-Goals

**Goals:**
- An `IdentityProvider` interface with a `LocalProvider`. `m2-active-directory` adds an `ActiveDirectoryProvider` behind the same interface.
- Per-request session checks that are cheap: one catalogue lookup per request.

**Non-Goals:**
- TOTP for `admin` (MAY, v1.3 §0.2).
- Multiple administrators.
- Email-based flows.

## Decisions

### Catalogue tables
This change adds a catalogue revision holding the v1.3 §4.1 tables:
- `users`, with `account_type`, `username_normalized`, `password_hash`, `must_change_password`, `role`, `active`, `session_version` and `last_login_at`;
- `auth_settings`, a single row holding `password_policy_json`, `access_token_minutes`, `refresh_token_hours`, `throttle_policy_json` and `revision`;
- `login_throttle`;
- `refresh_tokens`, holding `jti`, `family_id`, `expires_at`, `revoked_at` and `replaced_by`;
- `audit_events`;
- `bootstrap_tokens`, holding a token hash, `expires_at` and `consumed_at`, with a unique partial index ensuring one consumption.

Two partial unique indexes back the `users` rules:
- `username_normalized` is unique where `account_type='local'`;
- `role` is unique where `role='admin'`, which enforces the single administrator.

### Passwords
- **Hashing:** Argon2id via `argon2-cffi`, with library-default parameters that can be tuned through configuration. Hashes are rehashed on sign-in when the parameters change.
- **Timing equalisation:** an unknown username is verified against a fixed dummy hash.

### Tokens
- **Library:** Flask-JWT-Extended with `JWT_TOKEN_LOCATION=["cookies"]`, `JWT_COOKIE_CSRF_PROTECT=True` and `JWT_COOKIE_SAMESITE="Lax"`.
- **Secure flag:** `JWT_COOKIE_SECURE` is true except in workstation mode.
- **Refresh cookie path:** `/api/v1/auth/refresh`.
- **Signing key:** read from `secret_material/session_signing.key`.
- **Claims:** `sub` (user UUID), `prov` (provider), `sv` (session version) and `ar` (the `auth_settings` revision at issue).
- **Revalidation:** a `user_lookup_loader` with an additional check rejects the token when the account is inactive, `sv` differs from the account's or `ar` differs from the current settings.
- **Refresh tokens:** recorded in `refresh_tokens`. Reuse is detected when a token with `replaced_by` set is presented, and then the whole family is revoked.
- **CSRF failures:** Flask-JWT-Extended's default 401 is converted to 403 `FORBIDDEN` so the error contract stays consistent.

### Bootstrap
- **Token:** 32 random bytes, encoded in base32 for readability, with a 30-minute TTL. Only its Argon2 hash is stored.
- **Token file:** written with the same ACL helper as the data root.
- **Consumption:** an `UPDATE ... WHERE consumed_at IS NULL AND expires_at > now`, followed by insertion of the admin user in the same catalogue transaction. The unique admin-role index guarantees that only one setup can succeed.

### Throttling
- **Storage:** a sliding window held in `login_throttle`, with keys `ip:<addr>` and `id:<provider>:<normalized>`.
- **Backoff:** exponential, starting at 1 s and capped at 15 min.
- **`admin`:** the per-identifier key is skipped for `admin`, so the IP key is the only limit.
- **Response:** 429 `AUTH_THROTTLED` with `Retry-After`.

### Setup gate
A `before_request` hook checks a cached "admin exists" flag and returns 503 `SETUP_REQUIRED` outside the allowlist.

### Error code additions
`SETUP_REQUIRED` (503), `AUTH_THROTTLED` (429) and `PASSWORD_CHANGE_REQUIRED` (a `FORBIDDEN` detail) are added to the error registry and recorded in `docs/decisions.md`. v1.3 lists no codes for these situations.

## Risks / Trade-offs

- [The catalogue is read on every request] → It is a single indexed primary-key lookup, and WAL readers do not block writers.
- [IP throttling behind a proxy] → Correct client IPs depend on the trusted-proxy configuration (`m1-platform-foundation`). This is tested with spoofed headers.
- [Bootstrap token visible on the console] → It is short-lived and single-use, and the token file is permission-restricted. This is documented.

## Migration Plan

New catalogue revision applied by `litfoundry init` and `litfoundry migrate`. There is no earlier data.
