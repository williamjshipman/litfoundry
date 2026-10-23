# Tasks: M3 search strategy and query compilation

## 1. Strategy model

- [ ] 1.1 Write `docs/query-ast.schema.json` and the structural validator (`not` only under `and`, exactly one child), with node-path errors. Verify with schema fixture tests (§19 group 5).
- [ ] 1.2 Add the project revision for `source_selections`, `keyword_spec_versions`, `query_versions` and the draft strategy. Verify with migration tests.
- [ ] 1.3 Implement `GET`/`PUT /api/v1/projects/{project_id}/search-strategy` with `If-Match` and edit permission, plus source selection updates. Verify with API tests.
- [ ] 1.4 Implement immutable strategy-version capture, called by search runs. Verify with a unit test that later draft edits do not alter a captured version.

## 2. Compilers

- [ ] 2.1 Implement the Scopus compiler with golden fixtures (AND/OR/NOT, nested quotes, wildcards, years). Verify that the fixtures pass (§19 group 5).
- [ ] 2.2 Implement the WoS compiler (Starter tags, `PY=`, `DT=`, language warning). Verify with golden fixtures.
- [ ] 2.3 Implement the OpenAlex compiler (scoped search parameter, filters, URL encoding, mixed stemmed and wildcard rejection). Verify with golden fixtures, including the rejection case (§19 group 5).
- [ ] 2.4 Implement meaning-preserving splitting, refusing to split AND operands or OR groups inside NOT. Verify with a Hypothesis property test that the union of sub-query matches equals the original, plus explicit fixtures for the refused cases (§19 group 5).
- [ ] 2.5 Implement capability descriptors and warnings, including `UNSUPPORTED_FILTER`. Verify with unit tests.
- [ ] 2.6 Document query semantics per source in `docs/query-semantics.md`. Verify that every warning code is explained.

## 3. Preview and GUI

- [ ] 3.1 Implement `POST /api/v1/projects/{project_id}/queries/preview` (generated, override and effective queries, warnings, descriptors, call estimates), with counts behind the adapter `estimate()` interface. Verify with API tests and a fake adapter that asserts no outbound calls without counts.
- [ ] 3.2 Implement per-source overrides and query-version recording. Verify with API tests.
- [ ] 3.3 Build the search editor (groups, nesting, exclusion group, synonyms, scope, source switches, validation and credential status). Verify with a Playwright test that builds the v1.3 §7.1 example strategy.
- [ ] 3.4 Build the Source queries tab (side-by-side generated and effective queries, warnings, copy buttons, Scopus and WoS import instructions). Verify with a Playwright test.
- [ ] 3.5 Add the wizard strategy step. Verify with a Playwright test that the wizard creates the draft strategy and source selection.
