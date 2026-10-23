# Tasks: M2 project access control

## 1. Authorisation service

- [ ] 1.1 Add the catalogue revision for `project_acl`. Verify with a migration test.
- [ ] 1.2 Implement `authorize()` with the resolution order, explicit deny (never for admin) and disabled-account denial. Verify with a parametrised matrix test covering private, public view, public edit, explicit viewer, editor and deny, revocation and admin (§19 group 2).
- [ ] 1.3 Implement the `@project_permission` decorator with 404 for undiscoverable projects and 403 for insufficient rights. Apply it to every existing project route. Verify with forged-UUID and forged-URL tests (§19 groups 2 and 3).
- [ ] 1.4 Replace the owner-or-admin stub in `GET /api/v1/projects` with discovery through `authorize`. Verify with listing tests for shared and public projects.
- [ ] 1.5 Implement admin access audit entries in catalogue `audit_events` (one per project opening, one per change). Verify with API tests, including two openings in one session producing two events.
- [ ] 1.6 Add an authorisation test helper that asserts every registered project route declares a permission. Verify that it fails on a seeded undecorated route.

## 2. Sharing

- [ ] 2.1 Implement `GET`/`PUT /api/v1/projects/{project_id}/sharing` with visibility values, Public edit confirmation and per-user entries, restricted to owner and admin. Verify with API tests.
- [ ] 2.2 Implement the effective-permission preview with the deciding rule. Verify with unit tests.
- [ ] 2.3 Implement `GET /api/v1/users/lookup` (enabled accounts, minimal fields, rate limit). Verify with API tests, including a check that no email is returned.
- [ ] 2.4 Implement `GET /api/v1/projects/{project_id}/audit-events`, merging project and catalogue events. Verify with API tests.
- [ ] 2.5 Build the Sharing tab (visibility selector with Public edit warning, ACL editor with user lookup, preview, change log). Verify with a Playwright test (§19 group 12, sharing).
- [ ] 2.6 Document the access model and admin auditing in `docs/security.md`. Verify that the trust-model statement matches the About screen.
