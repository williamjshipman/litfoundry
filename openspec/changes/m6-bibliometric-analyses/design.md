# Design: M6 bibliometric analyses

## Context

Frozen corpora (`m5-corpus-and-prisma`) and canonical works with keyword rules (M4) exist. The job framework supports read-only jobs.

## Goals / Non-Goals

**Goals:**
- An analysis registry, so post-v1 analyses (6, 7, 10) can be added as new types without changing the run model.
- Deterministic outputs that can be checked against fixtures.

**Non-Goals:**
- Topic modelling (analysis 8, MAY).
- Bundling PyBibX or its ML stack.

## Decisions

### Registry
`AnalysisType(name, params_schema, required_fields, run(corpus_frame, params) -> Result)` is registered in `bibliometrics/registry.py`. The v1 types are:
- `annual_trends`
- `productivity`
- `citation_ranking`
- `coauthorship`
- `keywords`
- `overlap_completeness`

Unknown names are rejected.

### Engine adapter
- **Interface:** `BibliometricsEngine` with `capabilities()` and the calculation methods.
- **Biblium:** `BibliumEngine` is used only through documented interfaces, smoke-tested at startup, and its version is pinned.
- **Fallback:** `NativeEngine` implements every v1 calculation with pandas and NetworkX. Both engines run the same fixture tests, and results must match within tolerance.

### Determinism
- **Ordering:** input frames are sorted by work ID, and ties are broken by ID.
- **Randomness:** randomised layouts and clustering use a seeded RNG, and the seed is recorded in the parameters.
- **Input hash:** SHA-256 over the corpus `snapshot_sha256`, the parameters JSON, the engine version and a hash of the keyword dictionary's rule content at the recorded revision. Because the analysis reads only frozen data, equal input hashes mean equal inputs.

### Frozen reads
- **Source:** the job loads member data only from `corpus_work_metadata` for the corpus (`m5-corpus-and-prisma`), never from live `works` or entity tables. Later edits, merges or re-canonicalisation therefore cannot change an analysis of an existing corpus.
- **Dictionary:** keyword rules are applied from the immutable dictionary revision recorded for the run (`m4-canonical-records` keeps earlier revisions).
- **Large corpora:** frames are built in batches from the snapshot table.

### Artifacts
- **Storage:** written with the write-once helper to `figures/` or `reports/`, and recorded in `artifacts`.
- **CSV:** written with the formula-neutralising writer.
- **Downloads:** checksums are verified when an artifact is downloaded.

### Graph size
Networks are thresholded on the server, by top-N nodes and minimum edge weight, according to the parameters. The result reports the node and edge counts before and after thresholding.

## Risks / Trade-offs

- [Biblium's API changes] → Adapter plus smoke test, with the fallback always available.
- [Large networks are slow to lay out] → The server provides graph data only. Layout happens in the browser through ECharts force layout, with size limits.

## Migration Plan

Project revision adding `analysis_runs` and `artifacts`.
