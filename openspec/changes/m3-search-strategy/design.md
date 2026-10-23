# Design: M3 search strategy and query compilation

## Context

Projects, access control and jobs exist (M2). This change is mostly pure logic (AST and compilers) plus two endpoints, which makes it the most fixture-testable part of the system.

## Goals / Non-Goals

**Goals:**
- Compilers that are deterministic, versioned and covered by golden fixtures.
- A splitting algorithm that is provably equivalent to the original query.

**Non-Goals:**
- Executing searches (`m3-search-runs` and the adapters).
- Scopus API and WoS Expanded execution (post-v1). Their compilers are in scope.

## Decisions

### AST
- **Schema:** `docs/query-ast.schema.json` (JSON Schema draft 2020-12), validated with `jsonschema` (MIT).
- **Structural rules:** rules the schema cannot express (`not` only under `and`) are checked in Python after schema validation.
- **Stored form:** `keyword_spec_versions.ast_json` and `scope_json` hold the canonical JSON, with sorted keys for hashing.

### Compilers
- **Shape:** `compile(spec, options) -> CompiledQuery(text|params, warnings, sub_queries, compiler_version)`, one module per source. Each module has a `COMPILER_VERSION` constant that is bumped whenever output changes.
- **Golden tests:** `tests/fixtures/queries/*.json` hold AST inputs and the expected output per source, covering nested quotes, wildcards, NOT, year edges and empty scopes.
- **Scopus:** phrases use `"..."` for loose phrases, as v1.3 calls for phrase search within `TITLE-ABS-KEY`. Wildcards `*` and `?` pass through, and special characters are escaped.
- **WoS:** `TS=(...)` with `AND`/`OR`/`NOT`, `PY=2015-2026` and `DT=(Article OR Review)`. Only Starter tags are emitted.
- **OpenAlex:** Boolean syntax inside the `search.title_abstract_keywords` value. Wildcard leaves require the `.exact`-style unstemmed variant per OpenAlex docs, so a strategy mixing stemmed and wildcard leaves raises `INVALID_QUERY` with an explanation. Filters cover `publication_year`, `type` and `language`.

### Splitting
- **Measure:** the encoded URL length is measured with the real base URL and filters.
- **Choosing the node:** the splittable node is the largest OR node not under a NOT, along a path of AND/OR from the root.
- **Partitioning:** greedy bin-packing partitions its children so each sub-query fits.
- **Equivalence:** sub-query k is the original AST with that OR node replaced by partition k. The union equals the original, because AND distributes over OR.
- **Second-level splitting:** if one partition is still too long, the algorithm recurses into the next eligible OR node. If none remains, the query raises `INVALID_QUERY` with the message "query too long to split safely".
- **Proof test:** a property-based test (Hypothesis, MPL-2.0, test-only) evaluates random ASTs on random document sets and asserts that the union of the sub-queries' matches equals the original's matches.

### Preview
- **Estimates:** estimated calls are `ceil(estimated_results / page_size) × sub_queries`, where `estimated_results` comes from a count call only when counts are requested.
- **Count interface:** counts go through the adapter `estimate()` interface. This change defines the interface with a fake adapter, and the real adapters implement it.

## Risks / Trade-offs

- [OpenAlex query syntax evolves] → The compiler version records which syntax was used. Fixtures are updated deliberately, and the v1.3 A.3 pre-release check covers the current docs.
- [Scopus phrase semantics differ, `"..."` versus `{...}`] → Document the chosen semantics in `docs/query-semantics.md`, and show them in the preview explanation.

## Migration Plan

Project revision adding `source_selections`, `keyword_spec_versions`, `query_versions` and the draft strategy (stored in `project_info` with a revision).
