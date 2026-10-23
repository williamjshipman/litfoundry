# Design: M5 corpus snapshots and PRISMA reporting

## Context

The screening ledger (`m5-screening`), reports and studies (`m5-full-text-eligibility`), and merges and source memberships (M4) hold all the events PRISMA counts derive from.

## Goals / Non-Goals

**Goals:**
- Counts that are a pure function of recorded events plus adjustments.
- A corpus hash that is identical across export and import.

**Non-Goals:**
- PRISMA extensions such as PRISMA-ScR checklist generation.
- Editing diagrams by hand.

## Decisions

### Corpus hash
SHA-256 of the UTF-8 JSON:

```json
{"members": ["<work-id>", "..."], "studies": ["..."], "protocol_version_id": "...", "search_run_ids": ["..."]}
```

- **Serialisation:** sorted keys, sorted arrays and no whitespace.
- **IDs:** work, study, protocol and run IDs are kept on import (only the project UUID is rekeyed, v1.3 §15), so the hash survives.
- **Frozen snapshot:** freezing copies, in one read transaction, everything later readers of the corpus need into snapshot tables keyed by `corpus_id`, inside `project.sqlite`, so they travel with project exports:
  - `corpus_work_metadata(corpus_id, work_id, metadata_json)`: the canonical fields analyses and reports use;
  - `corpus_prisma_inputs(corpus_id, kind, payload_json)`: identification per source run, merges, decisions and resolutions (the ledger), retrieval attempts, reports and study links.
- **Snapshot hash:** `snapshot_sha256` is a SHA-256 over the canonical serialisation (sorted keys and rows) of both tables for the corpus. It is separate from the corpus hash, because v1.3 defines the corpus hash inputs.
- **Size:** a 50,000-work corpus snapshot is tens of MB of compressed JSON. Storage quotas count it.

### Count engine
A pure function, `compute_counts(frozen_inputs) -> PrismaCounts`. It reads only `corpus_prisma_inputs` for the corpus, never live tables, so counts cannot drift after freezing. Its sources, all as frozen:

| Count | Derived from |
|---|---|
| Identified per source | Distinct source records in the corpus's search runs, plus imports |
| Duplicates removed | Merges among those records |
| Screened, excluded | Final decisions at `title_abstract` |
| Sought, not retrieved | Retrieval attempts |
| Assessed, excluded with reasons | Final decisions at `full_text` |
| Included | Studies and reports |

The checks are linear equalities between stages. Adjustments are added per stage, with a justification.

### Diagram rendering
- **Library:** `prisma-flow` (import `prismaflow`), pinned exactly, behind `PrismaRenderer`.
- **Fallback:** when the library fails or lacks a feature, a native SVG template renderer is used.
- **PNG:** through the library when available, otherwise omitted (v1.3 "when available").
- **Rendering mode:** both renderers run headless on the worker. The SVG is static, with no scripts.

### Disclosure
Text templates are keyed by protocol method and the stages performed, and stored in `review/prisma/disclosure/`.

## Risks / Trade-offs

- [`prisma-flow` is alpha (v1.3 A.3)] → It is pinned and adapter-wrapped, and the fallback renderer is tested. Golden SVG structure tests cover both renderers.
- [Count definitions are ambiguous for multi-report studies] → They follow PRISMA 2020 (reports versus studies) and are documented with examples in `docs/data-model.md`.

## Migration Plan

Project revision adding `corpus_snapshots` (with `snapshot_sha256`), `corpus_members`, `corpus_work_metadata`, `corpus_prisma_inputs` and `prisma_snapshots`, with adjustment storage in `prisma_adjustments`.
