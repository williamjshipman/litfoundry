# Tasks: M3 Web of Science Starter source

## 1. Adapter

- [ ] 1.1 Implement the Starter adapter's `capabilities` (Starter tags, no language filter), `validate_credentials` and `estimate`, with the `X-ApiKey` header. Verify with fixture tests that the key is absent from URLs and request records, and that a run with no effective key fails with `AUTH_REQUIRED` before any request.
- [ ] 1.2 Implement page-number retrieval (50 per page), quota accounting and the configurable retrievable limit that marks the run `partial`. Verify with multi-page, quota and limit fixtures (§19 group 6).
- [ ] 1.3 Implement Starter normalisation and missing-field flags. Verify with fixture assertions.
- [ ] 1.4 Implement the DOI enrichment phase through the OpenAlex lookup, with an enrichment source run, field attribution and a warning when no OpenAlex key exists. Verify with fixtures for matched, unmatched and no-key cases (§19 group 6).
- [ ] 1.5 Implement the coverage summary and the screening-queue flag for missing abstracts. Verify with API tests.
- [ ] 1.6 Wire WoS counts into the query preview. Verify with an API test using fixtures.
- [ ] 1.7 Document Starter limits, enrichment and the WoS export-file route for full records. Verify that the docs list the pre-release checks.
