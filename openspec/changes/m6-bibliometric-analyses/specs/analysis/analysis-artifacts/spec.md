# Spec Delta: analysis/analysis-artifacts

## Purpose

Records every generated table, figure, graph, diagram and report as a checksummed artifact with full provenance, and serves artifacts only to authorised users.

## ADDED Requirements

### Requirement: Artifact records
Every generated output SHALL be stored write-once and recorded as an artifact with:
- kind;
- relative path, SHA-256, size and MIME type;
- creation time;
- the analysis run it came from, where there is one.

#### Scenario: Table artifact
- **WHEN** an analysis writes its ranking table as CSV
- **THEN** an artifact record with the file's SHA-256 and the analysis run ID exists

### Requirement: Artifact provenance
Each artifact SHALL be traceable to:
- the corpus hash;
- the parameters;
- the engine and software versions;
- the timestamp and creator;
- its file checksum.

#### Scenario: Trace a figure
- **WHEN** a user inspects a figure artifact
- **THEN** its corpus hash, parameters and software versions are shown

### Requirement: List artifacts
`GET /api/v1/projects/{project_id}/artifacts` SHALL list artifacts, filterable by kind, analysis run and corpus, to users with read access.

#### Scenario: Filter by run
- **WHEN** a user lists artifacts for one analysis run
- **THEN** only that run's artifacts are returned

### Requirement: Authorised retrieval
`GET /api/v1/projects/{project_id}/artifacts/{artifact_id}` SHALL serve the file only to users with read access, checked at request time. It SHALL verify the file's checksum before serving and refuse to serve a mismatched file.

#### Scenario: Tampered file
- **WHEN** an artifact file's content no longer matches its recorded SHA-256
- **THEN** retrieval fails with an error and the administrator is alerted

### Requirement: Export formats
Tables SHALL be exportable as CSV and JSON. Figures and graphs SHALL be exportable as SVG and, where supported, PNG.

#### Scenario: Export table
- **WHEN** a user exports an analysis table
- **THEN** CSV and JSON artifacts are available

### Requirement: Spreadsheet-safe CSV
CSV exports SHALL neutralise cells beginning with `=`, `+`, `-` or `@`, so bibliographic text cannot execute as spreadsheet formulas.

#### Scenario: Formula in title
- **WHEN** a work title starts with `=HYPERLINK(`
- **THEN** the exported CSV cell is prefixed so it is treated as text
