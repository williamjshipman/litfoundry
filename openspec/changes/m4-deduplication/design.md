# Design: M4 deduplication

## Context

The canonical works and source memberships come from `m4-canonical-records`. Write scopes and `RECORD_LOCKED` come from `m2-background-jobs`.

## Goals / Non-Goals

**Goals:**
- Near-linear candidate generation through blocking.
- Merge operations that are exactly reversible.

**Non-Goals:**
- Machine-learned matching.
- Cross-project deduplication.

## Decisions

### Normalisation for matching
- **Title:** NFKC normalisation, casefold, punctuation removed, whitespace collapsed and leading articles stripped.
- **DOI:** lowercase, with `https://doi.org/` stripped.
- **Authors:** first-author surname plus initials.

### Blocking
Each work gets these keys:
- `year` and `year±1`;
- the first 3 title tokens;
- the title's sorted rarest 2 trigrams.

Pairs are generated within each block and de-duplicated across blocks. The limit is configurable per block: an oversized block is split by the next key. The fixture asserts that the comparisons made are far fewer than all pairs.

### Scoring
- **Similarity:** RapidFuzz `token_set_ratio` for titles and Jaccard for author sets.
- **Factors:** year delta, venue equality and identifier conflict.
- **Score:** a weighted combination. Thresholds and weights are versioned and stored with each candidate.

### Merge mechanics
- **The merge:** sets `works.merged_into_work_id` and moves `work_sources` rows to the retained work, with an `origin_work_id` kept. The retained work's canonical values are recomputed through the precedence rule.
- **Recording:** `merge_decisions.originals_json` captures the pre-merge state (memberships and selected fields) for an exact undo.
- **Screening decisions:** not moved. The screening layer resolves decisions through `merged_into` chains (`m5-screening`).

### Jobs
- **Detection:** `dedup_detect`, an `append`-scope job that writes candidates only. It runs after canonicalisation completes, or on demand.
- **Changes:** merge and undo are `records`-scope jobs with the affected work IDs, so interactive edits to those works receive `RECORD_LOCKED`.

## Risks / Trade-offs

- [Blocking misses duplicates with very different titles] → Identifier stages catch most of them. The blocking keys are documented, and the recall test fixture includes typo and subtitle variants.
- [Auto-merge errors] → Each automatic merge is reversible and listed in the queue as `merged`. The setting can be turned off.

## Migration Plan

Project revision adding `duplicate_candidates` and `merge_decisions`, `origin_work_id` on `work_sources`, and the auto-merge project setting.
