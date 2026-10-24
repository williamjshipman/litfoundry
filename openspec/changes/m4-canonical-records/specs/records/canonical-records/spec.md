# Spec Delta: records/canonical-records

## Purpose

Turns source records from every provider into one canonical record per work. Each canonical record keeps field-level provenance, conflicting values and per-source citation data, so users can trust and trace every value.

## ADDED Requirements

### Requirement: Canonicalisation after retrieval
After a search or import completes, a background job SHALL link every new normalised source record to a canonical work. It SHALL record which source runs each work came from. Canonicalisation SHALL be incremental and idempotent.

#### Scenario: Records after import
- **WHEN** an import of 200 records completes
- **THEN** each record is linked to a canonical work and the works list grows accordingly

#### Scenario: Re-run is idempotent
- **WHEN** canonicalisation runs twice over the same source records
- **THEN** no additional works or links are created

### Requirement: Raw records are append-only
Raw source records and their stored payloads SHALL never be modified or deleted by canonicalisation, editing or merging.

#### Scenario: Edit canonical title
- **WHEN** an editor corrects a canonical title
- **THEN** the raw records still hold the original titles

### Requirement: Canonical work content
A canonical work SHALL hold:
- title, abstract, year and date;
- normalised DOI and other identifiers (OpenAlex ID, UT, PMID, EID, ISSN);
- language, document type and journal or source;
- authors, affiliations and keywords;
- per-source citation counts;
- cited references.

#### Scenario: Work detail fields
- **WHEN** a user opens a work with OpenAlex and WoS sources
- **THEN** the canonical fields and all identifiers from both sources are shown

### Requirement: Field-level provenance
For each canonical field, the system SHALL record:
- which source record and provider supplied the value;
- its retrieval date;
- the different values other sources supplied for that field.

#### Scenario: Conflicting years
- **WHEN** OpenAlex gives year 2021 and WoS gives 2022 for the same work
- **THEN** the work shows the selected year with its provider, and lists the other provider's value as a conflict

### Requirement: Deterministic value selection
Canonical values SHALL be selected from the sources by a documented, deterministic precedence rule. Editors SHALL be able to override a field by choosing a value or entering a correction. Each override SHALL be recorded with actor, time and reason, and SHALL be shown as a manual override.

#### Scenario: Manual override
- **WHEN** an editor selects the WoS title instead of the OpenAlex title
- **THEN** the canonical title changes, with provenance "manual override" naming the editor

### Requirement: Citation counts per source
Citation counts SHALL be stored and shown per source with their retrieval date. They SHALL never be summed across sources. Any derived summary, such as the maximum across sources, SHALL be labelled as derived.

#### Scenario: Two citation counts
- **WHEN** a work has OpenAlex and WoS citation counts
- **THEN** both are shown with source and date, and no total is shown as a citation count

### Requirement: Works are never deleted
Canonical works SHALL never be deleted. A work merged into another SHALL keep its ID and point to the retained work.

#### Scenario: Resolve merged work
- **WHEN** a client requests a work ID that was merged into another
- **THEN** the response identifies the retained work it was merged into

### Requirement: Record list
`GET /api/v1/projects/{project_id}/records` SHALL return works with server-side pagination, sorting and filtering, to users with read access. Filters SHALL include text, year range, source, document type, missing abstract, missing references and merged state.

#### Scenario: Filter by source
- **WHEN** a user filters records to those found in WoS Starter
- **THEN** only works with a WoS source membership are returned

### Requirement: Record detail
`GET /api/v1/projects/{project_id}/records/{record_id}` SHALL return a work with:
- its canonical fields and per-field provenance;
- conflicting values;
- per-source citations;
- its reference list;
- its source memberships.

#### Scenario: Provenance in detail
- **WHEN** a user opens a work's detail
- **THEN** each field shows its source, and other sources' values are listed

### Requirement: Record edits use optimistic concurrency
Edits to a canonical work SHALL require `If-Match` with the work's revision. They SHALL be refused with 409 `RECORD_LOCKED` while a running job holds that work.

#### Scenario: Stale record edit
- **WHEN** an editor saves a work using an outdated revision
- **THEN** the response is 409 `CONFLICT`

### Requirement: Records screen
The Records tab SHALL show a server-paginated, filterable table of works with a detail drawer. The drawer SHALL show per-source provenance, citations, reference lists and source overlap. All metadata SHALL be rendered as text.

#### Scenario: Open drawer
- **WHEN** a user selects a row in the Records table
- **THEN** the drawer shows that work's provenance and sources
