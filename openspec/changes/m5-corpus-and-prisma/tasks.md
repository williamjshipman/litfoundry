# Tasks: M5 corpus snapshots and PRISMA reporting

## 1. Corpora

- [ ] 1.1 Add the project revision for `corpus_snapshots`, `corpus_members`, `corpus_work_metadata`, `corpus_prisma_inputs`, `prisma_snapshots` and `prisma_adjustments`. Verify with migration tests.
- [ ] 1.2 Implement `POST`/`GET /api/v1/projects/{project_id}/corpora` with membership rules per method, the frozen metadata and PRISMA-input snapshots taken in one read transaction, the snapshot hash and partial-run acknowledgement. Verify with API tests for systematic, scoping and bibliometric fixtures.
- [ ] 1.3 Implement the canonical corpus hash. Verify with a unit test that it excludes the project UUID and is stable across serialisation order (§19 group 9).
- [ ] 1.4 Verify the immutability of frozen corpora and the resolution of merged members. Verify with tests that edit metadata, change decisions, record retrieval attempts and merge members after freezing, asserting that the frozen snapshots and their hash are unchanged.

## 2. PRISMA

- [ ] 2.1 Implement `compute_counts` over the frozen PRISMA inputs only, and the conservation checks with diagnostics. Verify with reconciliation fixtures, including unresolved conflicts and multi-report studies (§19 group 8), and a test that edits after freezing do not change a corpus's counts.
- [ ] 2.2 Implement justified adjustments and validation gating. Verify with API tests.
- [ ] 2.3 Implement metadata-only handling (no full-text stage) and the disclosure templates. Verify with a scoping-without-full-text fixture (§19 group 8, metadata-only mode).
- [ ] 2.4 Implement `PrismaRenderer` with the `prisma-flow` adapter and the native SVG fallback, the exclusion CSV, the JSON counts and snapshots, stored as artifacts. Verify with golden SVG-structure tests for both renderers.
- [ ] 2.5 Implement `GET .../prisma/{corpus_id}`, `POST .../adjustments` and `POST .../export`. Verify with API tests.

## 3. GUI and docs

- [ ] 3.1 Build the PRISMA tab (stages, counts, diagnostics, adjustments, preview, download). Verify with a Playwright test (§19 group 12, PRISMA SVG).
- [ ] 3.2 Document the count definitions and corpus hash in `docs/data-model.md`, and record the M4→M5 corpus placement in `docs/decisions.md`. Verify that every PRISMA box maps to a defined count.
