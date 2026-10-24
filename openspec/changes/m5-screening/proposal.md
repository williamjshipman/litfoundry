# Proposal: M5 review protocols and screening

## Why

LitFoundry supports full PRISMA-guided reviews, not just bibliometric mapping (v1.3 decision 6). Screening must follow a versioned protocol. Reviewer decisions are independent, append-only events. Disagreements between reviewers need recorded resolutions, so that the PRISMA counts and the frozen corpus can be traced back to individual decisions (v1.3 §11).

## What Changes

- **Review protocols:**
  - immutable versions (`/protocols`);
  - research questions, inclusion and exclusion criteria, review type (systematic, scoping or bibliometric), scope dates, databases and search dates;
  - reviewer policy (single or dual, with adjudication);
  - structured exclusion reason codes.
- **Screening rounds** per stage, for title/abstract and full text.
- **Reviewer decisions** (include, exclude or uncertain) with reason codes and notes:
  - decisions are append-only and versioned;
  - in dual mode, reviewers do not see each other's decisions until they have decided;
  - optimistic concurrency and `RECORD_LOCKED` apply.
- **Conflicts and final decisions:**
  - conflict detection;
  - resolution records (`/screening/resolutions`);
  - derivation of the final decision in single and dual modes.
- **Screening queue:**
  - excludes merged works;
  - flags missing abstracts;
  - bulk decisions run as `records`-scope jobs.
- **GUI:**
  - a screening screen with keyboard shortcuts, progress and per-stage counts;
  - the Protocol tab;
  - the wizard's review-mode step.

## Capabilities

### New Capabilities

- `review/review-protocols`: protocol versions, reviewer policy and exclusion reason codes.
- `review/screening`: screening rounds, reviewer decisions, independence, conflicts, resolutions, final decisions and the screening workflow.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §1: decision 6;
  - §4.2: the `review_protocol_versions`, `screening_rounds`, `record_screening_decisions` and `screening_resolutions` tables;
  - §11: the protocol, identification and title/abstract bullets;
  - §13: the wizard review mode, Protocol and Screening tabs;
  - §14: `/protocols`, `/screening/decisions` and `/screening/resolutions`;
  - §19: group 8 (dual reviewer and adjudication);
  - §20: M5.
- **Depends on:** `m4-deduplication`. Full-text decisions reuse this decision model (`m5-full-text-eligibility`).
- **Code:** `src/litfoundry/review/`, the project migration revision, the API routes and the frontend Protocol and Screening screens.
- **Out of scope:** ASReview import and export (`post-v1-asreview-interop`).
