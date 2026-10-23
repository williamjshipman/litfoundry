# Tasks: M2 Active Directory sign-in

## 1. Configuration and connection

- [ ] 1.1 Add the catalogue revision for `directory_config` and `directory_identity_bindings` (unique SID, unique user). Verify with migration tests.
- [ ] 1.2 Implement `DirectoryClient` over ldap3 with TLS validation, a server pool, timeouts and no referrals. Verify with unit tests against ldap3 MOCK and an integration test against the Samba AD DC container.
- [ ] 1.3 Implement `GET`/`PUT`/`DELETE /api/v1/admin/ad-directory`, with a write-only encrypted service-account password, a required service account and revisioning. Verify with API tests.
- [ ] 1.4 Implement `POST /api/v1/admin/ad-directory/test` (per-controller TLS, certificate, service bind and search, sanitised output) and gate enabling on a passing test of the current revision. Verify with tests for bad CA, wrong hostname and expired service account (§19 group 2).
- [ ] 1.5 Implement disable and delete, which revoke AD sessions through the directory revision claim. Verify that AD sessions are rejected and local sessions survive.
- [ ] 1.6 Implement admin-only diagnostic events for domain, certificate and service-account failures. Verify with API tests.

## 2. Sign-in

- [ ] 2.1 Implement `ActiveDirectoryProvider`: identifier forms, `admin` rejection, lookup-first with escaping and an attribute allowlist, the provisioning and account-state check before any user bind, the user bind with empty-password rejection, and generic timed failures. Verify with mock tests that assert no user bind occurs for unprovisioned, disabled or locked accounts, and with an LDAP injection test (§19 group 2).
- [ ] 2.2 Apply AD throttling (default 3 per identifier per 15 min), `DIRECTORY_UNAVAILABLE` and `AUTH_PROVIDER_DISABLED`. Verify with tests showing that the fourth attempt is throttled without a directory call, that `admin` signs in while the domain is down, and that AD sign-in is refused while AD is disabled.
- [ ] 2.3 Add the method selector to the sign-in page when `/api/v1/auth/methods` reports AD. Verify with a Playwright test.
- [ ] 2.4 Refuse local password operations for AD users. Verify with API tests.

## 3. Revalidation

- [ ] 3.1 Implement the `ad_revalidation` periodic job (disable, lock, delete and SID change revoke sessions) and grace-period enforcement for mutations. Verify with mock tests and a container outage test.

## 4. Provisioning

- [ ] 4.1 Implement `POST /api/v1/admin/ad-directory/resolve-user` with `AD_IDENTITY_AMBIGUOUS`. Verify with API tests.
- [ ] 4.2 Extend `POST /api/v1/admin/users` for AD-bound users, and `PATCH /api/v1/admin/users/{user_id}` for rebinding (`rebind` object) and local↔AD conversion (`conversion` object, while a direct account-type change stays rejected), with collision checks, session revocation and audit events. Verify with API tests, including duplicate SID and renamed `sAMAccountName`.
- [ ] 4.3 Build Admin → Authentication (AD settings, test, enable/disable, lockout guidance) and Admin → Users → New → Active Directory. Verify with a Playwright test against the test directory in which the admin configures AD, provisions a user and that user signs in (§19 group 12).
- [ ] 4.4 Document AD prerequisites (controller and CA trust, service-account rights, lockout threshold) in `packaging/directory/` and `docs/security.md`. Verify that the docs cover each configuration field.
