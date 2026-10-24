# Tasks: M5 full-text eligibility

## 1. Eligibility model

- [ ] 1.1 Add the project revision for `full_text_reports`, `retrieval_attempts`, `attachments`, `study_groups` and `study_work_links`. Verify with migration tests.
- [ ] 1.2 Implement full-text stage entry from final title/abstract includes, and full-text decisions with multiple reasons. Verify with API tests (§19 group 8).
- [ ] 1.3 Implement `GET`/`POST /api/v1/projects/{project_id}/retrieval-attempts`. Verify with API tests.
- [ ] 1.4 Implement `GET`/`POST .../studies` with separate study, report and work counts. Verify with a two-reports-one-study test.
- [ ] 1.5 Assert that external links are never fetched. Verify with a request-recording transport test.

## 2. Attachments

- [ ] 2.1 Implement upload (streaming, signature check, size and quota, optional scanner, SHA-256 de-duplication, write-once storage). Verify with tests for a disguised executable, quota, scanner rejection and duplicates (§19 group 14).
- [ ] 2.2 Implement authorised list, download (safe headers, per-request check) and logical delete with housekeeping removal. Verify with API tests, including no-access and post-revocation downloads (§19 group 14).

## 3. GUI and docs

- [ ] 3.1 Build the Full-text eligibility tab (retrieval, reports, decisions, studies, counts) and the Files tab. Verify with a Playwright test.
- [ ] 3.2 Document the attachment security policy and the no-fetch rule in `docs/security.md`. Verify that the docs list the allowed types and the scanner configuration.
