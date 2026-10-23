# Spec Delta: analysis/bibliometric-analyses

## Purpose

Runs reproducible bibliometric analyses on frozen corpora. Each analysis exposes its parameters, reports its coverage limits honestly and records full provenance.

## ADDED Requirements

### Requirement: Start an analysis
`POST /api/v1/projects/{project_id}/analyses` SHALL let editors, owners and the administrator start an analysis of a supported type on a frozen corpus, with validated parameters. It SHALL respond 202 with a job. Unsupported types or invalid parameters SHALL be rejected with `VALIDATION_ERROR`.

#### Scenario: Start keyword analysis
- **WHEN** an editor starts a keyword co-occurrence analysis on a frozen corpus
- **THEN** a job is queued and an analysis run record is created

#### Scenario: Unsupported type
- **WHEN** a client requests analysis type `topic_evolution`
- **THEN** the request is rejected with `VALIDATION_ERROR`

### Requirement: Analysis status and results
`GET /api/v1/projects/{project_id}/analyses` SHALL list analysis runs. `GET /api/v1/projects/{project_id}/analyses/{analysis_id}` SHALL return a run's status, configuration, warnings and results (paginated tables and graph data) to users with read access.

#### Scenario: Read results
- **WHEN** a viewer opens a completed analysis
- **THEN** its parameters, warnings and results are returned

### Requirement: Frozen input only
Analyses SHALL read work data only from the corpus's frozen metadata snapshot, never from live canonical records. They SHALL never modify project data, and they SHALL be able to run in parallel within the configured limits.

#### Scenario: Edits after freeze
- **WHEN** a member work's canonical title is edited after the corpus was frozen and an analysis then runs
- **THEN** the analysis uses the title as it was at freeze time

### Requirement: Annual publication trends
The system SHALL provide annual publication counts and trends (analysis 1) for a corpus, by year.

#### Scenario: Year counts
- **WHEN** analysis 1 runs on a fixture corpus with known years
- **THEN** the counts per year equal the fixture's known counts

### Requirement: Productivity rankings
The system SHALL rank authors, journals or sources, institutions and countries by number of works (analysis 2). It SHALL state the disambiguation method and identifier coverage used.

#### Scenario: Country coverage warning
- **WHEN** 30% of works lack affiliation countries
- **THEN** the country ranking shows a coverage warning stating 70% coverage

### Requirement: Citation rankings
The system SHALL rank works by citation count, per source, with the count's source and retrieval date and citations per year (analysis 3). It SHALL never sum counts across sources. Rankings SHALL be labelled as citation counts, not as quality measures.

#### Scenario: Per-source ranking
- **WHEN** a corpus has OpenAlex and WoS citation counts
- **THEN** the ranking is shown per selected source, with source and date labels

### Requirement: Coauthorship networks
The system SHALL build coauthorship collaboration networks (analysis 4) at author, institution or country level, with the selected thresholds, normalisation and graph-size limits.

#### Scenario: Known network
- **WHEN** analysis 4 runs on a small fixture with known coauthorships
- **THEN** the network's nodes and weighted edges match the fixture

### Requirement: Keyword analysis
The system SHALL compute keyword frequencies and co-occurrence networks (analysis 5), applying the project's keyword dictionary revision, which it SHALL record.

#### Scenario: Dictionary applied
- **WHEN** keyword rules map two variants to one keyword
- **THEN** the frequency table counts them as one keyword and records the dictionary revision

### Requirement: Source overlap and completeness
The system SHALL report source and database overlap and metadata completeness per field and source (analysis 9).

#### Scenario: Overlap table
- **WHEN** analysis 9 runs on a corpus from OpenAlex and WoS
- **THEN** it reports works unique to each source and shared, and per-field completeness

### Requirement: Exposed parameters
Each analysis type SHALL declare its parameters with types, defaults and ranges. The parameters cover thresholds, normalisation, network type, similarity measure, clustering parameters, time slicing, keyword dictionary version and graph size. Every run SHALL record the parameters it used.

#### Scenario: Out-of-range parameter
- **WHEN** a minimum-occurrence threshold of -1 is submitted
- **THEN** the request fails with `VALIDATION_ERROR`

### Requirement: Prerequisite fields
An analysis SHALL fail with an explanation when its essential fields are absent from the corpus. It SHALL warn, with a coverage percentage, when they are only partly present.

#### Scenario: No affiliations
- **WHEN** an institution ranking runs on a corpus with no affiliation data
- **THEN** the analysis fails and explains that affiliations are missing

### Requirement: Determinism and provenance
The same frozen corpus snapshot, parameters, keyword dictionary revision and software versions SHALL produce identical results. The input hash SHALL cover the corpus snapshot hash, the parameters, the dictionary's rule content and the engine version. Each run SHALL record:
- the corpus hash, the corpus snapshot hash and the input hash;
- the parameters;
- the engine name and version, and the versions of the other key libraries;
- timestamps and creator.

#### Scenario: Re-run reproducibility
- **WHEN** an analysis is run twice with the same inputs
- **THEN** the results and the input hash are identical

### Requirement: Engine fallback
When the primary bibliometrics engine is unavailable or lacks a needed capability, the essential calculations for the v1 analyses SHALL still run on the built-in fallback, and the run SHALL record which engine produced it.

#### Scenario: Engine unavailable
- **WHEN** the primary engine fails its capability check
- **THEN** analysis 1 still runs on the fallback and the run records the fallback engine
