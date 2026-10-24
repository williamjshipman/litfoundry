# Tasks: M3 source file imports

## 1. Pipeline

- [ ] 1.1 Implement `POST /api/v1/projects/{project_id}/source-imports`: streaming upload, SHA-256, size limit and a 202 job. Verify with API tests, including oversize rejection.
- [ ] 1.2 Implement signature-based format detection, encoding detection and content-safety checks. Verify with fixtures for wrong declared format and binary content.
- [ ] 1.3 Implement the repeated-file warning with confirmation. Verify with an API test.
- [ ] 1.4 Store the file write-once, create a source run (`file_import`, declared provider, retrieved count, scope `none`, `licensed` flag for Scopus and WoS) and use batched `append`-scope inserts. Verify with integration tests, including an import listed under its provider in search history.

## 2. Parsers

- [ ] 2.1 Add the BibTeX and RIS parsers with per-record error reporting. Verify with fixtures, including one malformed record (§19 group 7).
- [ ] 2.2 Add the Scopus CSV parser, keeping cited references. Verify with a real anonymised export fixture.
- [ ] 2.3 Add the WoS plain-text, tab-delimited and BibTeX parsers, keeping cited references. Verify with fixtures.
- [ ] 2.4 Add the OpenAlex JSON import through the adapter normaliser. Verify with a fixture.

## 3. GUI and docs

- [ ] 3.1 Build the import dialog (source, format, upload, progress, report). Verify with a Playwright test.
- [ ] 3.2 Document supported export settings per provider, including cited references for Scopus and WoS. Verify that the docs give the export steps for each format.
