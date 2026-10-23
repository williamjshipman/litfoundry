# Tasks: M3 OpenAlex source

## 1. Adapter

- [ ] 1.1 Implement the OpenAlex adapter's `capabilities`, `validate_credentials` and `estimate`, with the key required and sent as a Bearer header. Verify with fixture tests that the key never appears in URLs or the executed-request record.
- [ ] 1.2 Implement `retrieve_page` with cursor paging, filters, rate spacing and 429 backoff. Verify with multi-page and 429 fixtures (§19 group 6).
- [ ] 1.3 Implement cost recording from `X-RateLimit-Credits-Used`, with a default when the header is absent. Verify with budget tests using cost-header fixtures.
- [ ] 1.4 Implement split-query execution with de-duplicated union counts (temporary SQLite ID table). Verify with an overlapping sub-query fixture asserting reported count = distinct IDs (§19 group 5).
- [ ] 1.5 Implement `normalize` (abstract reconstruction, identifiers, authors, institutions, countries, keywords, topics, references, citation date) and missing-field flags. Verify with fixture assertions.
- [ ] 1.6 Implement the batched DOI lookup with unmatched reporting. Verify with a DOI batch fixture.
- [ ] 1.7 Wire OpenAlex counts into the query preview. Verify with an API test using fixtures.
- [ ] 1.8 Document OpenAlex key, cost and budget behaviour in `docs/query-semantics.md` and the admin guide. Verify that the docs state the pre-release check.
