# Tasks: M2 project workspaces

## 1. Schemas and migrations

- [ ] 1.1 Add catalogue revisions for `project_directory` (states, `relative_path`, `project_schema_version`) and `system_leases`. Verify with migration tests.
- [ ] 1.2 Create the project-template Alembic environment and the first revision (`project_info`, `project_audit_events`, `project_people`). Verify that a programmatic upgrade on a temporary project database reaches head.
- [ ] 1.3 Implement `litfoundry migrate`: maintenance lease, pre-migration backup, catalogue then each project, integrity checks, recorded versions, and restore on failure. Verify with fixture databases at prior versions and a deliberately failing script (§19 group 4).
- [ ] 1.4 Implement the schema version gate for `serve` and `worker`, and the project-level gate. Verify with startup tests for older and newer catalogue versions.
- [ ] 1.5 Report migration status in readiness, `litfoundry status` and the admin system screen. Verify with API and CLI tests.

## 2. Project storage

- [ ] 2.1 Implement `ProjectDatabaseRouter` (`NullPool`, PRAGMAs per connect, state and version re-check, containment). Verify with unit tests and a forged-UUID test (§19 group 3).
- [ ] 2.2 Implement staged provisioning with atomic rename and clean-up on failure. Verify with fault-injection tests at each step.
- [ ] 2.3 Implement the write-once file helper (temporary name, fsync, `os.replace`), placing each file before the database row that references it is committed. Verify with a kill-during-write test and a test that no committed row references a missing file.
- [ ] 2.4 Write `manifest.json` (product, UUID, schema version, no absolute paths). Verify with a unit test.
- [ ] 2.5 Implement `litfoundry reconcile` for orphan `provisioning` rows, folders without rows and stuck `deleting` projects. Verify with crash-simulation fixtures.
- [ ] 2.6 Add a Windows CI test that deletes a project immediately after another process used it. Verify it passes on the Windows runner (§19 group 3).

## 3. Lifecycle API

- [ ] 3.1 Implement `GET`/`POST /api/v1/projects` and `GET`/`PATCH /api/v1/projects/{project_id}` with `If-Match`, using owner-or-admin access for now. Verify with API tests.
- [ ] 3.2 Implement archive and unarchive with read-only enforcement (`PROJECT_ARCHIVED`). Verify with API tests.
- [ ] 3.3 Implement two-stage `DELETE` with confirmation, the `deleting` state, a bounded wait for in-flight operations, the move to `trash/` and audited housekeeping purge. Verify with API and housekeeping tests.
- [ ] 3.4 Implement `transfer-ownership` and the admin `transfer-projects`, with no file moves and audit events. Verify with tests that the folder path is unchanged (§19 group 3).
- [ ] 3.5 Implement admin quarantine and release, `PROJECT_UNAVAILABLE` for `deleting`, `quarantined` and `error`, and integrity-failure detection that raises an admin alert. Verify with API tests and a corrupted-database fixture.
- [ ] 3.6 Document the project lifecycle, storage layout and migration procedure in `docs/architecture.md` and `docs/data-model.md`. Verify that the docs describe each state transition.

## 4. GUI

- [ ] 4.1 Build the Home page (owned, shared and visible groups, filters, create button). Verify with a Playwright test.
- [ ] 4.2 Build the new-project wizard's project-details step and the workspace frame with the Overview and History/settings tabs. Verify with a Playwright test that creates and opens a project.
- [ ] 4.3 Add archive, delete (with the export prompt and title confirmation) and transfer actions to History/settings. Verify with a Playwright test.
