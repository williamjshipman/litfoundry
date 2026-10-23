# Proposal: Co-citation and bibliographic coupling analyses (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Design and tasks will be written when this change is scheduled.

## Why

Co-citation networks (analysis 6) and bibliographic coupling (analysis 7) show the intellectual structure of a field, but both depend on cited references (v1.3 §12). v1 already keeps cited references from OpenAlex and from Scopus and WoS exports. This change adds the two analyses as new analysis types under the v1 analysis framework.

## What Changes

- **Analysis 6:** co-citation networks of cited works or sources.
- **Analysis 7:** bibliographic coupling of corpus works.
- **Reference matching:** references are matched across sources, by identifiers first and normalised reference strings second, and the match method and rate are reported.
- **Parameters:** similarity measures, normalisation, thresholds and graph size.
- **Coverage:** the analyses fail or warn, and report reference coverage, when cited references are missing or partial.

## Capabilities

### New Capabilities

- `analysis/citation-networks`: the co-citation and bibliographic coupling analyses, with reference matching and coverage reporting.

### Modified Capabilities

None. The new analysis types are added to the v1 analysis registry.

## Impact

- **v1.3 sections implemented:**
  - §0.2: analyses 6–7;
  - §12: analyses 6 and 7.
- **Depends on:** `m6-bibliometric-analyses` and `m6-reports-and-visualisations`.
- **Code:** `src/litfoundry/bibliometrics/citation_networks.py`.
