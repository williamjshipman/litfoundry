# Spec Delta: review/full-text-eligibility

## Purpose

Supports the PRISMA eligibility stage. It records which reports were sought and retrieved, assesses full texts with explicit exclusion reasons, and keeps works, reports and studies distinct.

## ADDED Requirements

### Requirement: Entry to full-text stage
When the current protocol includes a full-text stage, works whose final title/abstract decision is `include` SHALL enter the full-text stage.

#### Scenario: Included work advances
- **WHEN** a work's final title/abstract decision becomes include
- **THEN** it appears in the full-text eligibility queue

### Requirement: Full-text reports
Each work SHALL be able to have zero or more full-text reports. Each report has an attachment, an external link, or both, plus report metadata.

#### Scenario: Two reports for one work
- **WHEN** an editor adds a preprint and a published version as reports of one work
- **THEN** the work lists two reports

### Requirement: Retrieval attempts
`POST /api/v1/projects/{project_id}/retrieval-attempts` SHALL let editors record, for a work's report, an outcome of `retrieved`, `not_retrieved` or `not_sought`, with a reason and the actor. `GET` SHALL list attempts. Outcomes SHALL feed the PRISMA counts of reports sought and not retrieved.

#### Scenario: Not retrieved
- **WHEN** an editor records a report as not retrieved because of a paywall
- **THEN** the attempt is stored with the reason and counts as a report not retrieved

### Requirement: Full-text decisions
Full-text decisions SHALL use the screening decision, conflict and resolution model at stage `full_text`. An `exclude` decision SHALL require one or more reason codes from the protocol.

#### Scenario: Multiple reasons
- **WHEN** a reviewer excludes a full text for wrong population and wrong outcome
- **THEN** both reason codes are recorded on the decision

### Requirement: Studies
`GET` and `POST /api/v1/projects/{project_id}/studies` SHALL let editors create study groups and link works and reports to them. Counts of included studies SHALL be kept separate from counts of included reports and works.

#### Scenario: Two reports, one study
- **WHEN** two included works are linked to one study
- **THEN** included reports count 2 and included studies count 1

### Requirement: No full-text fetching
LitFoundry SHALL NOT download full texts from publishers or other external sites. External links SHALL be stored as entered and never fetched by the server.

#### Scenario: External link stored
- **WHEN** an editor saves an external link for a report
- **THEN** the link is stored and the server makes no request to it

### Requirement: Full-text eligibility tab
The Full-text eligibility tab SHALL show, per work:
- retrieval status;
- reports and attachments;
- reviewer decisions with reasons;
- study links.

It SHALL also show stage progress counts.

#### Scenario: Stage overview
- **WHEN** a user opens the Full-text eligibility tab
- **THEN** sought, retrieved, not retrieved, assessed, included and excluded counts are shown
