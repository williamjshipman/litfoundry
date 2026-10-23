# Design: M4 canonical records

## Context

`m3-search-runs` stores raw records and adapter-normalised `source_records`. This change builds the canonical layer that deduplication, screening and analyses use.

## Goals / Non-Goals

**Goals:**
- Provenance stored per field, cheap to query for the detail view.
- Canonicalisation that is incremental, so a new import does not rebuild 50,000 works.

**Non-Goals:**
- Duplicate detection and merging (`m4-deduplication`). In this change, each new source record becomes its own work, unless it is a DOI-identical enrichment record. Those are linked to their Starter work directly.

## Decisions

### Tables
The v1.3 §4.2 tables are added as listed. `work_sources.selected_fields_json` maps each canonical field to the `source_record_id` that supplied it, plus a `manual` marker. The field-level provenance and conflicts are held in `work_field_values(work_id, field, source_record_id, value_json, retrieved_at)`. This is a helper table, recorded in `docs/decisions.md`, that makes conflicts queryable.

### Precedence rule
Default precedence for each field:
1. a manual override;
2. a non-empty value from the source with that field's highest provider rank;
3. the most recent retrieval.

The provider ranks per field are:
- abstract: OpenAlex, then Scopus, then WoS;
- references: WoS export, then Scopus, then OpenAlex.

The rank table lives in `processing/precedence.py` and is documented in `docs/data-model.md`. The table version is recorded on each work.

### Entities
- **Authors:** normalised per work (name, ORCID when present). Cross-work author disambiguation uses ORCID or OpenAlex author IDs when present, otherwise the name string. This is documented as a limitation affecting analysis 2.
- **Affiliations:** institution names and countries are kept per source.
- **Cited references:** stored as provider IDs (OpenAlex W-IDs) and as raw reference strings from exports, and kept for post-v1 co-citation.

### Job
The canonicalisation job is an `append`-scope job, triggered when a search or import job completes. It processes source records that are not yet linked, in batches.

### Records query
SQLite FTS5 over title, abstract and keywords supports text search, with keyset pagination.

## Risks / Trade-offs

- [Author disambiguation is weak without identifiers] → Rankings are labelled with the disambiguation method used, and analyses report the share of authors with identifiers.
- [`work_field_values` grows large] → It is indexed by `(work_id, field)`. 50,000 works × about 10 fields × 2–3 sources is fine in SQLite.

## Migration Plan

Project revision adding the canonical tables, the FTS5 index and keyword rules.
