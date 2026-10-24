# Spec Delta: search/query-compilation

## Purpose

Translates the project strategy into each source's query language faithfully. Anything that cannot be translated is shown explicitly, never silently broadened, and users can review and override the result before running it.

## ADDED Requirements

### Requirement: Scopus compilation
The Scopus compiler SHALL produce a `TITLE-ABS-KEY(...)` expression with `PUBYEAR` year filters and the supported source filters. Phrases, wildcards and special characters SHALL be escaped correctly.

#### Scenario: Year range
- **WHEN** a strategy with years 2015–2026 is compiled for Scopus
- **THEN** the query contains `PUBYEAR > 2014 AND PUBYEAR < 2027`, or an equivalent valid form

### Requirement: Web of Science compilation
The WoS compiler SHALL produce a `TS=(...)` expression combined with a `PY=` year range and `DT=` document types, using only the Starter API field tags. A language filter SHALL produce a warning that it cannot be applied.

#### Scenario: Language not supported
- **WHEN** a strategy with a language filter is compiled for WoS Starter
- **THEN** the compiled query omits the language and the preview shows a warning

### Requirement: OpenAlex compilation
The OpenAlex compiler SHALL produce the scoped search parameter (`search.title_abstract_keywords` or `search.title_and_abstract`, per scope) plus work filters, URL-encoded. It SHALL record the exact parameters and their semantics.

#### Scenario: Title-abstract-keywords scope
- **WHEN** a strategy with scope `title_abstract_keywords` is compiled for OpenAlex
- **THEN** the request uses the `search.title_abstract_keywords` parameter

### Requirement: Stemming and wildcard conflict
A strategy that mixes stemmed terms with wildcard or fuzzy terms SHALL be rejected for OpenAlex with an explanation. This is because OpenAlex wildcards need the unstemmed exact variant. The query SHALL NOT be silently changed.

#### Scenario: Mixed query
- **WHEN** a strategy combines the stemmed term `flotation` with the wildcard `flotat*` for OpenAlex
- **THEN** OpenAlex compilation fails with an explanation and no OpenAlex query is produced

### Requirement: Meaning-preserving query splitting
When an OpenAlex request would exceed the URL length limit (about 4 KB), the compiler SHALL split the query only by partitioning the children of an OR node that is not inside a NOT, producing sub-queries whose union equals the original. It SHALL never split AND operands or OR groups inside a NOT. If no such split fits, compilation SHALL fail with an explanation.

#### Scenario: Long OR group
- **WHEN** a strategy has an OR group of 300 synonyms ANDed with another group
- **THEN** the compiler produces several sub-queries, each ANDing a subset of the synonyms with the other group

#### Scenario: Long NOT group
- **WHEN** only an OR group inside a NOT is too long
- **THEN** compilation fails rather than splitting it

### Requirement: Untranslatable logic is explicit
Any part of a strategy that a source cannot express SHALL produce a warning or an error. A compiler SHALL never silently broaden or narrow a query.

#### Scenario: Unsupported filter
- **WHEN** a document-type filter has no equivalent in a source
- **THEN** the preview shows an `UNSUPPORTED_FILTER` warning for that source

### Requirement: Source capability descriptors
Each source SHALL publish a capability descriptor covering:
- wildcards and quoted terms;
- field scopes and language and document-type filters;
- date filters;
- maximum query length;
- count support;
- cursor paging.

The GUI SHALL use descriptors to explain each source's limits.

#### Scenario: Descriptor in preview
- **WHEN** a client requests a query preview
- **THEN** each source's result includes its capability descriptor

### Requirement: Query preview
`POST /api/v1/projects/{project_id}/queries/preview` SHALL return, for each enabled source:
- the generated query, any override and the effective query;
- warnings;
- the estimated number of API calls (pages × sub-queries).

It SHALL make no API calls unless test counts are explicitly requested.

#### Scenario: Preview without counts
- **WHEN** an editor previews queries without requesting counts
- **THEN** compilations, warnings and call estimates are returned and no outbound request is made

#### Scenario: Preview with counts
- **WHEN** an editor requests test counts
- **THEN** each API source that supports counts returns a count, and the calls are charged to the effective credential's budget

### Requirement: Manual overrides
Editors SHALL be able to override the generated query per source. The effective query SHALL be the override when one is present, otherwise the generated query. The preview SHALL show the generated and effective queries side by side.

#### Scenario: Override used
- **WHEN** an editor overrides the Scopus query
- **THEN** the effective Scopus query is the override and the generated query remains visible

### Requirement: Recorded query versions
For each source used in a search, the system SHALL record:
- the generated, override and effective queries;
- the compiler version;
- the validation results.

These are linked to the strategy version.

#### Scenario: Query provenance
- **WHEN** a user inspects a past source run
- **THEN** it shows the compiler version and the exact effective query used

### Requirement: Copyable queries for manual sources
The Source queries tab SHALL offer each compiled query for copying. It SHALL include instructions to run Scopus and WoS queries in the provider's own interface and to import the export file.

#### Scenario: Copy Scopus query
- **WHEN** an editor opens the Source queries tab with Scopus enabled
- **THEN** the Scopus query can be copied and the import instructions are shown
