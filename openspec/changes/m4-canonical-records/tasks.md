# Tasks: M4 canonical records

## 1. Canonical model

- [ ] 1.1 Add the project revision for the canonical tables (`works`, identifiers, sources, entities, `work_references`, `citation_counts`, `work_field_values`, FTS5). Verify with migration tests.
- [ ] 1.2 Implement the canonicalisation job (`append` scope, incremental, idempotent, linked memberships, Starter enrichment linking by DOI). Verify with fixture imports from every M3 source (§19 group 7).
- [ ] 1.3 Implement the precedence rule with recorded table version, field provenance and conflict capture. Verify with conflicting-source fixtures.
- [ ] 1.4 Implement manual overrides with actor, reason and `If-Match`, honouring `RECORD_LOCKED`. Verify with API tests.
- [ ] 1.5 Store citation counts per source with date, never summed, with derived summaries labelled. Verify with unit tests.
- [ ] 1.6 Document the canonical model and precedence in `docs/data-model.md`. Verify that every field's precedence is listed.

## 2. Records API and GUI

- [ ] 2.1 Implement `GET /api/v1/projects/{project_id}/records` (FTS text, filters, sort, keyset pagination) and `GET .../records/{record_id}` with provenance and resolution of merged works. Verify with API tests on a 10,000-work fixture.
- [ ] 2.2 Build the Records table and detail drawer (provenance, conflicts, citations, references, source overlap, text-only rendering). Verify with a Playwright test, including an XSS title fixture.

## 3. Keyword normalisation

- [ ] 3.1 Implement keyword rules (`exact`, `wildcard`, `stopword`), validation (cycles, wildcard position) and immutable, retrievable dictionary revisions via `GET`/`PUT /api/v1/projects/{project_id}/keyword-rules`. Verify with API tests.
- [ ] 3.2 Implement the normalised keyword view that leaves stored keywords unchanged. Verify with unit tests.
- [ ] 3.3 Build the keyword-rules screen with a match preview. Verify with a Playwright test.
