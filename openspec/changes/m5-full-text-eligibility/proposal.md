# Proposal: M5 full-text eligibility

## Why

The PRISMA 2020 eligibility stage needs reports that were sought, retrieved or not retrieved, full-text assessment with explicit exclusion reasons, and a distinction between works, reports and studies. One study can have several reports (v1.3 §11). Full texts are uploaded by authorised users and must be stored and served securely, without circumventing paywalls.

## What Changes

- **Full-text stage:** works included at title/abstract enter the full-text stage when the protocol includes one. Full-text decisions reuse the screening decision model and allow one or more exclusion reasons.
- **Reports:** a work can have several full-text reports, each with an attachment or an external link and its own metadata.
- **Retrieval attempts:** `/retrieval-attempts` records each attempt's outcome (`retrieved`, `not_retrieved` or `not_sought`), its reason and its actor.
- **Studies:** `/studies` creates study groups that link works and reports to one study, and keeps study, report and work counts separate.
- **Attachments:** `/attachments` uploads, downloads and deletes full texts:
  - type and signature validation;
  - size limits and storage quotas;
  - SHA-256 de-duplication;
  - write-once storage;
  - authorised downloads;
  - an optional scan command.
- **No fetching:** LitFoundry never fetches full texts from publishers. External links are stored as given and never fetched by the server.
- **GUI:** the Full-text eligibility tab and the Files tab.

## Capabilities

### New Capabilities

- `review/full-text-eligibility`: the full-text stage, reports, retrieval attempts, full-text decisions and studies.
- `review/attachments`: secure upload, storage, download and deletion of full-text files.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `retrieval_attempts`, `attachments`, `full_text_reports`, `study_groups` and `study_work_links` tables;
  - §11: the eligibility, attachments and studies bullets;
  - §13: the Full-text eligibility and Files tabs;
  - §14: `/retrieval-attempts`, `/studies` and `/attachments`;
  - §17: the upload and download bullets;
  - §19: groups 8 (full-text retrieval and reasons) and 14 (download authorisation, unsafe paths);
  - §20: M5.
- **Depends on:** `m5-screening`.
- **Code:** `src/litfoundry/review/fulltext.py` and `attachments.py`, the API routes and the frontend tabs.
- **Dependency:** `python-magic`-free signature detection, so there is no libmagic in the bundle.
