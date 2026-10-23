# Spec Delta: review/asreview-interop

## Purpose

Lets teams use ASReview for prioritised title/abstract screening. LitFoundry exchanges files with ASReview while keeping human adjudication and honest recall claims.

## ADDED Requirements

### Requirement: Export screening input
`GET /api/v1/projects/{project_id}/screening/asreview` SHALL export a CSV of de-duplicated works awaiting title/abstract screening, with work IDs, titles, abstracts, authors, years and DOIs, for users with edit rights.

#### Scenario: Export
- **WHEN** an editor exports ASReview input
- **THEN** the CSV contains one row per unmerged work with its work ID

### Requirement: Import labelled results
`POST /api/v1/projects/{project_id}/screening/asreview` SHALL import an ASReview results file. It SHALL match rows by work ID and record each label as a decision attributed to the named reviewer, with origin `asreview`. Rows with unknown work IDs SHALL be reported and skipped.

#### Scenario: Unknown work ID
- **WHEN** an import file contains a row whose work ID is not in the project
- **THEN** that row is skipped and reported

### Requirement: Human adjudication required
Decisions imported from ASReview SHALL NOT become final decisions until a human reviewer confirms or adjudicates them.

#### Scenario: Imported include
- **WHEN** ASReview labels are imported
- **THEN** the affected works show the labels as awaiting human confirmation and are not counted as finally included

### Requirement: Recall disclosure
The GUI and reports SHALL state that prioritised screening does not guarantee complete recall whenever ASReview labels were used.

#### Scenario: Report disclosure
- **WHEN** a report covers a corpus screened with ASReview labels
- **THEN** its limitations section includes the recall disclosure

### Requirement: No embedded ASReview server
LitFoundry SHALL NOT require or embed an ASReview server.

#### Scenario: Offline interop
- **WHEN** ASReview is not installed on the LitFoundry host
- **THEN** export and import still work
