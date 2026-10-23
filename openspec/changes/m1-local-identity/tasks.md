# Tasks: M1 local identity

## 1. Catalogue identity schema

- [ ] 1.1 Add the catalogue revision for `users`, `auth_settings`, `login_throttle`, `refresh_tokens`, `audit_events` and `bootstrap_tokens`, with the partial unique indexes for local usernames and the single `admin` role. Verify with migration tests and an index-violation test.
- [ ] 1.2 Implement the `IdentityProvider` interface and `LocalProvider`, with Argon2id hashing and rehash-on-login. Verify with unit tests for hash verification and timing equalisation via the dummy hash.

## 2. Bootstrap and recovery

- [ ] 2.1 Implement the setup gate, `GET /api/v1/setup/status` and `POST /api/v1/setup/admin` with atomic token consumption. Verify with API tests, including concurrent setup attempts and setup after completion (§19 group 1).
- [ ] 2.2 Issue bootstrap tokens during `litfoundry init`, at first service start and through `litfoundry bootstrap-token`, writing a restricted token file and never logging the token. Delete the file on expiry (next start, housekeeping, or use of the expired token). Verify with CLI tests, an expiry test and a log scan for the token.
- [ ] 2.3 Implement `litfoundry admin reset-password`, which revokes `admin` sessions and writes an audit event. Verify with a CLI test.
- [ ] 2.4 Enforce the administrator invariants: no delete, rename or disable of `admin`, and no second admin. Verify with API tests (§19 group 1).
- [ ] 2.5 Build the setup page in the GUI. Verify with a Playwright test that completes bootstrap.

## 3. Local sign-in and passwords

- [ ] 3.1 Implement `POST /api/v1/auth/login` for the local provider, with a default provider, generic failures and username normalisation. Verify with API tests for case-insensitivity, unknown versus wrong password parity, invalid usernames and a rejected contact-email identifier (§19 group 2).
- [ ] 3.2 Implement the password policy, the forced-change gate and `PUT /api/v1/auth/password`, which revokes other sessions. Verify with API tests.
- [ ] 3.3 Implement throttling per IP and per identifier, with `admin` limited per IP only, returning 429 `AUTH_THROTTLED`. Verify with tests showing that `admin` signs in from a second IP while the first is throttled (§19 group 1).
- [ ] 3.4 Implement `GET`/`PUT /api/v1/admin/auth-settings` for policy, lifetimes and throttling, with a revision bump when a change invalidates sessions. Verify with API tests.

## 4. Sessions

- [ ] 4.1 Configure the JWT cookies (flags per run mode), CSRF double-submit and the conversion of CSRF failures to 403. Verify with cookie-flag tests for both modes and a missing-CSRF test (§19 group 14).
- [ ] 4.2 Implement refresh rotation with family revocation on reuse, and logout. Verify with API tests.
- [ ] 4.3 Implement per-request revalidation (active, `sv`, `ar`). Verify with tests for disable, password change and settings revision taking effect on the next request.
- [ ] 4.4 Implement `GET /api/v1/auth/me` and `GET /api/v1/auth/methods`. Verify with API tests, including a check that the method selector is hidden when only local sign-in exists.
- [ ] 4.5 Build the sign-in page and the forced password-change page in the GUI. Verify with Playwright tests, including a check that no token is in web storage.

## 5. User administration and audit

- [ ] 5.1 Implement `GET`/`POST /api/v1/admin/users`, `PATCH /api/v1/admin/users/{user_id}`, reset-password and revoke-sessions for local accounts. Verify with API tests for admin-only access, duplicate usernames, rejected direct account-type changes through PATCH (the conversion action arrives in `m2-active-directory`), and a route scan showing that no endpoint creates accounts except the admin ones.
- [ ] 5.2 Build Admin → Users (list, create, enable/disable, reset, revoke with confirmations). Verify with a Playwright test in which the admin creates a local user who then signs in (§19 group 12, local part).
- [ ] 5.3 Write audit events for the listed actions and implement `GET /api/v1/admin/audit-events` with filters and Admin → Audit. Verify with API tests for each audited action and admin-only access, plus a test that DELETE and PATCH on audit URLs are rejected.
- [ ] 5.4 Re-verify the admin-only checks on `/api/v1/health/ready` and `/api/v1/admin/logs` from `m1-platform-foundation`, now that identity exists. Verify with API tests.
- [ ] 5.5 Run the secret-leak scan over the identity test suite's logs, audit records and catalogue dumps. Verify that no password or token is found.

## 6. Branding and admin console screens (completing `m1-platform-foundation` GUI requirements)

- [ ] 6.1 Add the branded application header, sign-in and setup branding, and an HTML title containing `LitFoundry` on every page. Verify with a Playwright test of the title and tagline (§20 M1 acceptance).
- [ ] 6.2 Build the About screen (name, tagline, description, version, GPLv3 licence, administrator trust disclosure). Verify with a Playwright test.
- [ ] 6.3 Build Admin → System (versions, run mode, hostname, proxy configuration, readiness checks, no secrets). Verify with a Playwright test as `admin`, and a 403 test for a user.
- [ ] 6.4 Build the admin log view over `GET /api/v1/admin/logs` (level, process and correlation-ID filters). Verify with a Playwright test that filters by `request_id`.
- [ ] 6.5 Run the M1 acceptance checks from v1.3 §20: UI title and tagline, `litfoundry` CLI and import path, `LITFOUNDRY_` environment prefix, Caddy hostname example, and strict CSP with zero violations. Verify that all pass together.
