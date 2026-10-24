# Proposal: M4 deduplication

## Why

The same work arrives from several sources, and often more than once. PRISMA requires an honest count of duplicates removed. Bibliometric results are wrong if duplicates remain. Merges must never destroy raw records or earlier review decisions, and they must stay reversible, so frozen corpora remain resolvable (v1.3 §10).

## What Changes

- **Detection stages:**
  1. normalised DOI;
  2. other persistent identifiers;
  3. normalised exact title with year and authors;
  4. fuzzy matching with blocking keys, never comparing all pairs, sized so that 50,000 records stay within the job budget.
- **Automatic merges:** exact-identifier matches are merged automatically. This is a project setting, on by default. Each automatic merge is recorded as a reversible system merge decision.
- **Manual review:** uncertain candidates join a review queue with their score and the factors behind it. Likely conference-versus-journal versions are flagged rather than merged.
- **Decisions:** merge, reject, defer and undo, through `/duplicates` and `/duplicates/decisions`. Merges run as `records`-scope jobs.
- **Safety:** merged works keep their IDs and point to the retained work. Raw records and review decisions are preserved, and an undo restores the earlier state.
- **Overlap and PRISMA:** source membership drives source-overlap counts and the PRISMA duplicates-removed count.
- **GUI:** a side-by-side compare screen with confidence reasons, accept, reject and undo, and bulk safe actions.

## Capabilities

### New Capabilities

- `records/deduplication`: duplicate detection stages, the candidate queue, merge, reject, defer and undo decisions, merge safety and overlap accounting.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `duplicate_candidates` and `merge_decisions` tables;
  - §9: merges as `records`-scope jobs;
  - §10: from the second paragraph on;
  - §13: Dedup;
  - §14: `/duplicates` and `/duplicates/decisions`;
  - §19: group 7 (dedup with blocking, the 50,000-record fixture, reversible merges, the conference/journal case);
  - §20: M4.
- **Depends on:** `m4-canonical-records`.
- **Code:** `src/litfoundry/processing/dedup/`, the project migration revision, the API routes and the frontend Dedup screen.
- **Dependencies introduced:** RapidFuzz (MIT).
