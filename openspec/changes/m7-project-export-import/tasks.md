# Tasks: M7 project export and import

## 1. Export

- [ ] 1.1 Implement the export job: the `export:<project_uuid>` lease (no write scope), SQLite backup snapshot, inventory built from the snapshot's references, allowlisted contents, checksums, provenance, notice, branded name and manifest, `.partial` then verify then rename. Verify with an integration test that checks the contents and the absence of secrets (§19 group 11).
- [ ] 1.2 Implement the licensed-content acknowledgement (`EXPORT_RESTRICTED`) and the metadata-only option. Verify with API tests.
- [ ] 1.3 Implement `GET`/`POST /api/v1/projects/{project_id}/exports` and `GET .../exports/{export_id}/download`, with an owner-or-admin recheck. Verify with API tests, including a former owner after transfer.
- [ ] 1.4 Implement expiry housekeeping (default 7 days, skipped while the backup lease is held). Verify with a clock-controlled test (§19 group 11, export expiry).
- [ ] 1.5 Build the export screen (progress, acknowledgement, metadata-only, history, download). Verify with a Playwright test.
- [ ] 1.6 Make housekeeping skip a project's file deletions while its export lease is held. Verify with a test that deletes an attachment mid-export and asserts the file is exported, then removed afterwards.

## 2. Import

- [ ] 2.1 Implement archive validation (size, count, types, traversal, symlinks, ratio, manifest identifier and version, checksums) with configurable limits. Verify with hostile-archive fixtures (§19 group 11).
- [ ] 2.2 Implement quota-limited staging, migration of older schemas and rejection of newer schemas. Verify with fixtures from a prior schema version.
- [ ] 2.3 Implement rekeying, private defaults, cleared jobs and ACLs, imported people, imported-from provenance and atomic registration. Verify with API tests, including re-importing an export of a project that still exists, which must create a separate project.
- [ ] 2.4 Implement `POST /api/v1/project-imports` and the Home import action. Verify with a Playwright test.
- [ ] 2.5 Add a round-trip test (export, then import) asserting schema, checksums, corpus and corpus snapshot hashes, artifacts, ledgers and reviewers on Windows, Linux and macOS CI. Verify that it passes on all three (§19 group 11).
- [ ] 2.6 Document the export format, exclusions and import validation in `docs/`. Verify that the manifest fields are listed.
