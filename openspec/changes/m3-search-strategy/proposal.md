# Proposal: M3 search strategy and query compilation

## Why

Reviewers define one keyword strategy and need it translated faithfully into each database's query language. They also need to see exactly what will run and what cannot be translated (v1.3 §7). Query compilers for all three sources are MUST even where v1 has no API adapter: users run the compiled Scopus query in Scopus's own interface and import the export file (v1.3 A.2).

## What Changes

- **Strategy representation:**
  - a canonical Boolean AST with leaves for terms and phrases, published as `docs/query-ast.schema.json`;
  - every stored strategy is validated against the schema;
  - the draft strategy is editable with optimistic concurrency;
  - immutable strategy versions are captured whenever a search runs;
  - per-project source selection toggles.
- **Compilers for Scopus, WoS and OpenAlex:**
  - Scopus: `TITLE-ABS-KEY` and `PUBYEAR`;
  - WoS: `TS=`, `PY=` and `DT=`, using the Starter tag set;
  - OpenAlex: scoped search parameters and filters, rejection of mixed stemmed and wildcard queries, URL-length-aware splitting that preserves meaning;
  - explicit warnings for logic a source cannot express.
- **Capability descriptors:** each source declares what it supports.
- **Query preview** at `/projects/{project_id}/queries/preview`:
  - generated and overridden queries side by side;
  - warnings;
  - estimated API calls;
  - optional test counts;
  - manual per-source overrides.
- **GUI:**
  - the search strategy editor;
  - the Source queries tab, with copyable Scopus and WoS queries and import instructions;
  - the wizard's strategy step.

## Capabilities

### New Capabilities

- `search/search-strategy`: the strategy AST and schema, draft editing, immutable versions, source selection and the strategy editor.
- `search/query-compilation`: per-source compilers, capability descriptors, warnings, overrides, splitting and the query preview.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §4.2: the `source_selections`, `keyword_spec_versions` and `query_versions` tables;
  - §7;
  - §13: the new-project wizard (strategy step), Search editor and Source queries tab;
  - §14: `/search-strategy` and `/queries/preview`;
  - §19: group 5;
  - §20: M3.
- **Depends on:** `m2-project-workspaces` and `m2-project-access-control`.
- **Later work:** estimated calls and test counts use adapters and budgets from `m3-source-credentials`, `m3-openalex-source` and `m3-wos-starter-source`. Until they land, preview returns compilations and warnings only.
- **Code:** `src/litfoundry/queries/` (AST, schema validation, three compilers), the project migration revision, the API routes and the frontend strategy and query screens.
