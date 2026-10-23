# Proposal: M3 source file imports

## Why

v1 has no Scopus API adapter and no WoS Expanded adapter. File imports are therefore the route for:
- Scopus records;
- full WoS records with cited references;
- records from institutions without API entitlements.

v1.3 requires a manual-import path for every source (§0, §8). Imported records must carry the same provenance as API results and count in PRISMA.

## What Changes

- **Upload endpoint:** `POST /projects/{project_id}/source-imports`. It takes a multipart upload with the declared source and format, and imports in the background.
- **Supported formats:**
  - BibTeX (`.bib`);
  - RIS (`.ris`);
  - Scopus CSV;
  - WoS plain text, tab-delimited and BibTeX exports;
  - OpenAlex JSON.
- **Validation:**
  - size, encoding and format;
  - record count;
  - content safety;
  - per-record errors with locations;
  - a warning, needing confirmation, when the same file content was imported before.
- **Provenance:** each import creates a source run with `origin=file_import`, no query version and `credential_scope_used=none`. The original file is stored write-once with its SHA-256, and records are normalised into the same source-record form as API results.
- **Cited references:** kept from Scopus and WoS exports, for later co-citation and coupling analyses.
- **Licensed sources:** Scopus and WoS imports are marked as licensed, so exports can warn about redistribution rights.
- **GUI:** an import dialog with progress and a validation report.

## Capabilities

### New Capabilities

- `search/source-file-imports`: uploading, validating, parsing and recording bibliographic export files as provenance-preserving source runs.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §8: the Scopus file import, the WoS export formats and Manual import;
  - §14: `/source-imports`;
  - §19: group 7 (import and provenance);
  - §20: M3 (file imports for Scopus, WoS and OpenAlex).
- **Depends on:** `m3-search-runs`.
- **Code:** `src/litfoundry/sources/importers/` (one parser per format) and fixture files in `tests/fixtures/imports/`.
- **Dependencies introduced:** `bibtexparser` (MIT) and `rispy` (MIT), subject to the licence review.
