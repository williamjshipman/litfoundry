# Proposal: M4 canonical records

## Why

Records arrive from OpenAlex, WoS Starter, enrichment and file imports, each with different fields and gaps. Screening and bibliometrics need one canonical record per work. That record must still show where every field came from and where the sources disagree. Citation counts must never be summed across sources as if they were unique (v1.3 §10).

## What Changes

- **Canonicalisation:** a background job builds canonical `works` from normalised source records, recording:
  - field-level provenance;
  - the values each source supplied where sources conflict;
  - retrieval dates;
  - work-to-source membership.

  It runs after each search or import completes. Raw records stay append-only.
- **Canonical values:** a deterministic, documented rule picks each field's value from the sources, and editors can override it with an audited choice.
- **Citations:** counts are kept per source, with source and date, and never summed.
- **Identifiers and entities:** works carry DOI, OpenAlex ID, UT, PMID and EID. Authors, affiliations, keywords and cited references are canonicalised.
- **Records API and GUI:**
  - `/records` (search, sort, filter, paginate) and `/records/{record_id}` (detail with provenance);
  - the Records table with its detail drawer.
- **Keyword normalisation:** project rules (`/keyword-rules`) with a versioned dictionary, used by analyses.

## Capabilities

### New Capabilities

- `records/canonical-records`: canonical works, field provenance and conflicts, per-source citations, identifiers, and the records API and GUI.
- `records/keyword-normalisation`: project keyword normalisation rules and their versioned dictionary.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `works`, `work_identifiers`, `work_sources`, `authors`, `affiliations`, `work_authors`, `work_affiliations`, `keywords`, `work_keywords`, `work_references`, `citation_counts` and `keyword_normalization_rules` tables;
  - §10: first paragraph;
  - §13: Records;
  - §14: `/records` and `/keyword-rules`;
  - §19: group 7 (normalisation and provenance);
  - §20: M4.
- **Depends on:** `m3-search-runs` and `m3-source-file-imports`. The adapters (`m3-openalex-source`, `m3-wos-starter-source`) provide real input but are not required for the fixtures.
- **Code:** `src/litfoundry/processing/` (canonicaliser, provenance, keyword rules), the project migration revision, the API routes and the frontend Records and keyword-rules screens.
