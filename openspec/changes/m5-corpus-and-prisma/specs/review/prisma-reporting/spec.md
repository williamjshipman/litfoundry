# Spec Delta: review/prisma-reporting

## Purpose

Produces PRISMA flow counts and diagrams derived from recorded events. Counts are validated for consistency, corrections are justified openly, and the result is honest about which review stages were actually performed.

## ADDED Requirements

### Requirement: Derived counts
`GET /api/v1/projects/{project_id}/prisma/{corpus_id}` SHALL return PRISMA counts derived from the recorded events frozen with that corpus:
- records identified per source (API and file imports);
- duplicates removed;
- records screened and excluded;
- reports sought and not retrieved;
- reports assessed and excluded, with counts per reason;
- studies and reports included.

#### Scenario: Counts from events
- **WHEN** a user requests PRISMA counts for a corpus
- **THEN** every count is computed from the corpus's frozen source runs, merges, decisions, retrieval attempts and studies

### Requirement: Counts stable after freeze
The derived counts for a frozen corpus SHALL be computed only from its frozen inputs. Later screening, retrieval, merge or study edits SHALL NOT change them. Justified adjustments SHALL remain the only way to change a frozen corpus's reported counts.

#### Scenario: Decision changed after freeze
- **WHEN** a reviewer changes a full-text decision after a corpus was frozen
- **THEN** the PRISMA counts for that corpus are unchanged, and a corpus frozen later reflects the change

### Requirement: Conservation checks
The engine SHALL validate that counts reconcile between stages. For example, records identified minus duplicates removed must equal records screened. Any discrepancy SHALL be reported as a diagnostic with the stage and difference.

#### Scenario: Unresolved conflicts
- **WHEN** some title/abstract conflicts are unresolved
- **THEN** validation reports them as a discrepancy at the screening stage

### Requirement: Justified adjustments
`POST /api/v1/projects/{project_id}/prisma/{corpus_id}/adjustments` SHALL let editors record a manual count adjustment with stage, amount and justification. Adjustments SHALL be stored separately from derived counts and shown as adjustments. They SHALL never overwrite derived values.

#### Scenario: Adjust for records from other sources
- **WHEN** an editor adds 12 records identified from citation searching, with a justification
- **THEN** the diagram shows the adjustment and its justification separately from the derived counts

### Requirement: Validation before diagram
Diagram generation SHALL be refused while validation reports unexplained discrepancies. A discrepancy is explained when a justified adjustment accounts for it.

#### Scenario: Blocked export
- **WHEN** an editor exports a diagram while a discrepancy is unexplained
- **THEN** the export fails with `VALIDATION_ERROR` listing the diagnostics

### Requirement: Honest stages
If no full-text screening was conducted, the diagram and counts SHALL omit the full-text stage instead of fabricating it. Generated texts SHALL NOT claim full systematic-review compliance.

#### Scenario: Metadata-only review
- **WHEN** a scoping review is completed without full-text screening
- **THEN** the diagram has no eligibility stage and the disclosure states that full texts were not assessed

### Requirement: Diagram export
`POST /api/v1/projects/{project_id}/prisma/{corpus_id}/export` SHALL generate:
- a PRISMA 2020 flow diagram as SVG;
- the counts as JSON;
- a PNG where the renderer supports it;
- a machine-readable exclusion-reason table (CSV).

Each output SHALL be stored as an artifact with provenance.

#### Scenario: Export diagram
- **WHEN** an editor exports a validated PRISMA diagram
- **THEN** SVG, JSON and the exclusion table exist as artifacts linked to the corpus

### Requirement: PRISMA snapshots
Each export SHALL store a PRISMA snapshot with the counts, adjustments, exclusions, validation results and generation time.

#### Scenario: Snapshot stored
- **WHEN** a diagram is exported
- **THEN** a snapshot with the exact counts used is stored

### Requirement: Disclosure text
The system SHALL generate disclosure text that states whether the work is a PRISMA 2020 systematic or scoping review or a bibliographic mapping, and which stages were performed. The text SHALL be included in reports.

#### Scenario: Bibliometric disclosure
- **WHEN** a bibliometric-method corpus is reported
- **THEN** the disclosure describes it as bibliographic mapping, not a PRISMA 2020 review

### Requirement: PRISMA tab
The PRISMA tab SHALL show stages and counts, validation diagnostics, adjustments, a diagram preview and downloads.

#### Scenario: Preview
- **WHEN** a user opens the PRISMA tab for a validated corpus
- **THEN** the diagram preview and download links are shown
