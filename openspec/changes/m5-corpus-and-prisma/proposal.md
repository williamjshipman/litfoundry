# Proposal: M5 corpus snapshots and PRISMA reporting

## Why

Bibliometric results and PRISMA diagrams must be reproducible. They have to refer to a frozen, hashed set of included works and studies, plus the protocol and screening ledger that produced it (v1.3 §11). PRISMA counts must come from recorded events, not typed-in numbers. Manual corrections must be separately justified, and a review that skipped full-text screening must never be presented as if it had done it.

## What Changes

- **Corpus freezing (`/corpora`):** an immutable member set of works and studies, recorded with:
  - the selected search runs and the protocol version;
  - a snapshot of the screening-resolution ledger;
  - a snapshot of every member work's metadata and of every PRISMA count input, so analyses and counts for the corpus never change after freezing;
  - a SHA-256 over a canonical serialisation that excludes the project UUID, plus a separate hash of the frozen snapshot.

  Freezing over a partial source run needs explicit acknowledgement. Later edits create a new corpus version, and merged members still resolve.
- **PRISMA count engine:**
  - counts are derived from the corpus's frozen source runs, merges, screening, retrieval and studies;
  - conservation and reconciliation checks run with diagnostics;
  - justified manual adjustments are recorded separately (`/prisma/{corpus_id}/adjustments`);
  - metadata-only mode, with no fabricated full-text stage.
- **PRISMA export (`/prisma/{corpus_id}/export`):**
  - the PRISMA 2020 flow diagram as SVG, JSON and PNG where available;
  - a machine-readable exclusion-reason table;
  - disclosure text that distinguishes a PRISMA 2020 review from bibliographic mapping.
- **GUI:** the PRISMA tab with stages, counts, diagnostics, preview and download.

## Capabilities

### New Capabilities

- `review/corpus-snapshots`: frozen, hashed, versioned corpora with partial-source acknowledgement.
- `review/prisma-reporting`: the PRISMA count engine, validation, adjustments, metadata-only mode, diagram export and disclosure.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `corpus_snapshots`, `corpus_members` and `prisma_snapshots` tables;
  - §8: partial-run acknowledgement;
  - §11: the frozen corpus, count engine and `prisma-flow` bullets;
  - §13: PRISMA;
  - §14: `/corpora` and the `/prisma` routes;
  - §19: groups 8 (PRISMA reconciliation and metadata-only mode) and 9 (corpus hash and version reproducibility);
  - §20: M4 and M5.
- **Depends on:** `m5-screening` and `m5-full-text-eligibility`.
- **Departure from §20:** v1.3 §20 lists corpus versioning under M4. It is placed here because corpus membership depends on screening resolutions. Recorded in `docs/decisions.md`.
- **Code:** `src/litfoundry/review/corpus.py` and `prisma/`, the API routes and the frontend PRISMA tab.
- **Dependencies introduced:** `prisma-flow`, pinned to an exact version (alpha, BSD-3-Clause), behind an adapter with a native SVG fallback.
