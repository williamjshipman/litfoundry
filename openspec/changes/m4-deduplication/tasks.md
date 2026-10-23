# Tasks: M4 deduplication

## 1. Detection

- [ ] 1.1 Add the project revision for `duplicate_candidates`, `merge_decisions`, `origin_work_id` and the auto-merge setting. Verify with migration tests.
- [ ] 1.2 Implement the matching normalisation and the identifier and exact-title stages. Verify with unit fixtures.
- [ ] 1.3 Implement blocking and fuzzy scoring with recorded factors and versioned weights. Verify with recall fixtures (typos, subtitles) and the 50,000-work fixture within the budget, asserting the comparison count (§19 group 7).
- [ ] 1.4 Flag possible versions (conference versus journal). Verify with a fixture showing they are never auto-merged (§19 group 7).
- [ ] 1.5 Implement the `dedup_detect` job, triggered after canonicalisation. Verify with an integration test.

## 2. Decisions

- [ ] 2.1 Implement automatic exact-identifier merges as reversible system decisions. Verify with tests for the setting on and off.
- [ ] 2.2 Implement `GET /api/v1/projects/{project_id}/duplicates` and `POST .../duplicates/decisions` (merge, reject, defer, undo) as `records`-scope jobs. Verify with API tests, including `RECORD_LOCKED` during a merge.
- [ ] 2.3 Ensure merges preserve works, raw records and review decisions, and that undo restores memberships and values exactly. Verify with a round-trip test that compares database state before and after (§19 group 7).
- [ ] 2.4 Implement overlap and duplicates-removed accounting. Verify with a fixture of known overlap.

## 3. GUI and docs

- [ ] 3.1 Build the Dedup screen (side-by-side compare, factors, actions, bulk safe actions with confirmation). Verify with a Playwright test (§19 group 12, dedup).
- [ ] 3.2 Document the matching stages, blocking keys, thresholds and undo semantics in `docs/data-model.md`. Verify that the docs match the stored weight version.
