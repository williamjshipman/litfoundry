# Tasks: M5 review protocols and screening

## 1. Protocols

- [ ] 1.1 Add the project revision for protocols, rounds, decisions, resolutions and `screening_state`. Verify with migration tests.
- [ ] 1.2 Implement `GET`/`POST /api/v1/projects/{project_id}/protocols` (immutable versions, reviewer policy, reason codes, and the option to require title/abstract reasons, off by default). Verify with API tests.
- [ ] 1.3 Build the Protocol tab and the wizard review-mode step. Verify with a Playwright test.

## 2. Decisions and resolutions

- [ ] 2.1 Implement rounds and `POST`/`GET .../screening/decisions` (reasons required for full-text exclusions and for title/abstract exclusions only when the protocol says so, reason codes limited to the protocol's list, append-only versions, edit rights, optimistic concurrency, `RECORD_LOCKED`, closed-round rejection). Verify with API tests, including an unknown reason code.
- [ ] 2.2 Implement server-side blinding for dual screening. Verify with API tests showing the second reviewer cannot see the first reviewer's decision.
- [ ] 2.3 Implement conflict detection, `POST .../screening/resolutions` with adjudicator eligibility, and final-decision derivation. Verify with a dual-reviewer scenario test, including unresolved conflicts (§19 group 8).
- [ ] 2.4 Resolve decisions through merge chains. Verify with a merge-after-screening test.
- [ ] 2.5 Implement bulk decisions as chunked `records`-scope jobs. Verify with a job test.
- [ ] 2.6 Add the projection rebuild command and test it against the ledger. Verify that a rebuilt projection equals the live one.

## 3. GUI

- [ ] 3.1 Build the screening queue (excludes merged works, flags missing abstracts) and the screening screen with keyboard shortcuts, reasons and notes. Verify with a Playwright keyboard-only screening test (§19 group 12, screen).
- [ ] 3.2 Build progress and per-stage counts per reviewer, and the reconciliation view for adjudicators. Verify with a Playwright test.
- [ ] 3.3 Document the screening model and blinding in `docs/data-model.md`. Verify that the docs describe final-decision derivation.
