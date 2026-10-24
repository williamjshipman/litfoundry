# Tasks: M7 hardening and release acceptance

## 1. Quotas

- [ ] 1.1 Implement quota settings with documented defaults and `QuotaGuard` at project creation, upload, import, export and job submission (queued-jobs quota), returning `QUOTA_EXCEEDED`. Verify with API tests for each quota, the admin project-quota exemption, and a test that exceeding the concurrent-jobs limit queues rather than refuses.
- [ ] 1.2 Implement incremental storage usage with housekeeping reconciliation, and the usage views for admin, owner and user. Verify with tests.
- [ ] 1.3 Add the quotas to the configuration reference. Verify that each quota is documented with its default.

## 2. Performance and resilience

- [ ] 2.1 Build the load-test fixtures (10,000 source records, and 50,000 works) and the Locust scenario. Verify that the p95 targets hold on the reference machine, and record the results in `docs/`.
- [ ] 2.2 Add a slow-provider test showing that web requests are unaffected during a 30-second provider delay. Verify that it passes.
- [ ] 2.3 Add the crash and reboot resilience tests (kill during search, import, analysis and backup; reconcile; assert invariants). Verify that they pass on Windows and Linux CI.

## 3. Documentation

- [ ] 3.1 Write `docs/security.md`: trust model, deployment boundary, authentication, secrets, unencrypted backups, uploads and log redaction. Verify that its trust statement matches the About screen.
- [ ] 3.2 Write `docs/privacy.md`: the personal-data inventory with export and backup inclusion, and manual request handling and limits. Verify with a checklist against v1.3 §17.

## 4. Release acceptance (integration only)

- [ ] 4.1 Implement `tests/e2e/test_release_flow.py` covering the full §19 group 12 flow with the CSP-violation collector. Verify that it passes against a venv build on all three operating systems.
- [ ] 4.2 Run the release flow and smoke tests against the packaged build on a clean Windows host, and check every item of the v1.3 §19 definition of done (two LAN browsers over HTTPS, separate project folders, permissions, search, dedup, screening, PRISMA, analysis, export and import, migrations, CLI backup and offline restore, no secret leaks). Verify with a signed-off checklist in the release notes.
