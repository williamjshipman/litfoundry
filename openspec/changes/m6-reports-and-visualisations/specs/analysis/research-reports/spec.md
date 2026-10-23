# Spec Delta: analysis/research-reports

## Purpose

Produces versioned, self-contained HTML reports that present results together with their methods, sources, limitations and provenance, suitable for sharing and archiving.

## ADDED Requirements

### Requirement: Generate a report
`POST /api/v1/projects/{project_id}/reports` SHALL let editors, owners and the administrator generate an HTML report for a frozen corpus and selected analysis runs. It SHALL respond 202 with a job. The report SHALL be stored as a new versioned artifact, and earlier versions SHALL be kept.

#### Scenario: Second version
- **WHEN** an editor generates a report twice for the same corpus
- **THEN** two report versions exist as separate artifacts

### Requirement: Report content
A report SHALL draw its corpus data from the corpus's frozen snapshot, and SHALL contain:
- methods and search strategy, with the compiled queries, search dates and per-source counts and completeness;
- the PRISMA diagram and its disclosure text;
- the selected analyses' figures and tables, with their parameters;
- limitations and methodological notes, including coverage warnings;
- provenance: corpus hash, software versions and creation details.

#### Scenario: Partial source disclosed
- **WHEN** the corpus includes a partial source run
- **THEN** the report's limitations section states which source was partial and why

### Requirement: Citation counts are not quality scores
Reports SHALL label citation counts with their source and date. They SHALL state that citation counts are not measures of quality.

#### Scenario: Citation section wording
- **WHEN** a report includes a citation ranking
- **THEN** the section labels each count's source and date and includes the quality caveat

### Requirement: Self-contained and safe
Report HTML SHALL contain no scripts and no external references, with figures embedded as static SVG or images. All bibliographic text SHALL be escaped. The report SHALL display correctly offline.

#### Scenario: Hostile title in report
- **WHEN** a work title contains HTML markup
- **THEN** the report shows the literal text and contains no executable content

### Requirement: Reports tab
The Reports tab SHALL let editors choose a corpus and analyses, generate reports, list report versions and download them.

#### Scenario: Download report
- **WHEN** a viewer opens the Reports tab
- **THEN** existing report versions are listed and can be downloaded
