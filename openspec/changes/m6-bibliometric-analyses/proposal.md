# Proposal: M6 bibliometric analyses

## Why

Bibliometric analysis is the product's second purpose, alongside PRISMA screening. Results must be reproducible from a frozen corpus and honest about coverage gaps. They must never present citation counts as quality scores, or placeholder numbers as findings (v1.3 §0, §12). v1 ships analyses 1–5 and 9. Analyses 6, 7 and 10 are SHOULD, and analysis 8 is MAY (v1.3 §0.2).

## What Changes

- **Analysis runs (`/analyses`):** analyses run as read-only background jobs on a frozen corpus, reading only the metadata snapshot taken when the corpus was frozen. Their parameters are validated, and each run records full provenance: corpus hash, parameters, engine and software versions, keyword dictionary version, timestamps and creator.
- **v1 analyses:**
  1. annual publication counts and trends;
  2. productive authors, sources, institutions and countries;
  3. citation rankings, with source and date, citations per year and coverage warnings;
  4. coauthorship networks;
  5. keyword frequency and co-occurrence networks;
  9. source and database overlap, and metadata completeness.
- **Parameters exposed:** thresholds, normalisation, network type, similarity measure, clustering parameters, time slicing, keyword dictionary version and graph size limits.
- **Missing data:** a run fails or warns when its prerequisite fields are missing, and reports coverage.
- **Determinism:** results are deterministic for the same inputs.
- **Engine:** Biblium is used behind a `BibliometricsEngine` adapter, with capabilities checked at runtime. A tested pandas/NetworkX fallback covers the essential calculations, and the engine used is recorded.
- **Artifacts (`/artifacts`):** every generated table, figure and graph is stored with a checksum and provenance, and served through authorised retrieval.

## Capabilities

### New Capabilities

- `analysis/bibliometric-analyses`: analysis runs, the v1 analysis types, parameters, prerequisites, determinism and provenance.
- `analysis/analysis-artifacts`: artifact records, provenance, checksums, listing and authorised retrieval.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `analysis_runs` and `artifacts` tables;
  - §12: analyses 1–5 and 9, parameters, provenance and the engine adapter;
  - §14: `/analyses` and `/artifacts`;
  - §19: group 9;
  - §20: M6.
- **Depends on:** `m5-corpus-and-prisma` and `m4-canonical-records` (keyword rules).
- **Code:** `src/litfoundry/bibliometrics/`, the project migration revision and the API routes.
- **Dependencies introduced:** pandas, numpy, scipy and NetworkX, all BSD. Biblium (MIT) is pinned, and its transitive licences are reviewed.
- **Out of scope:** analyses 6, 7 and 10 (`post-v1-citation-networks`, `post-v1-research-maturity`), analysis 8 (MAY, which needs its own specification), and PyBibX and BibFusion connectors (MAY).
