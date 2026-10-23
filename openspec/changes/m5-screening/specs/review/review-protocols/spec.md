# Spec Delta: review/review-protocols

## Purpose

Records the review protocol (questions, criteria, method and reviewer policy) as immutable versions, so screening and reporting can always cite the exact protocol they followed.

## ADDED Requirements

### Requirement: Protocol content
A protocol version SHALL record:
- research questions;
- inclusion and exclusion criteria;
- the review method (`systematic`, `scoping` or `bibliometric`);
- scope dates, databases and search dates;
- the reviewer policy;
- the list of structured exclusion reason codes.

#### Scenario: Create protocol
- **WHEN** an editor saves a systematic-review protocol with criteria and reason codes
- **THEN** a protocol version with those fields exists

### Requirement: Immutable protocol versions
`POST /api/v1/projects/{project_id}/protocols` SHALL create a new protocol version for editors, owners and the administrator. Existing versions SHALL never change. `GET` SHALL list all versions, with the current one marked.

#### Scenario: Revise protocol
- **WHEN** an editor changes the criteria
- **THEN** a new version is created and the earlier version is unchanged

### Requirement: Reviewer policy
The reviewer policy SHALL specify single or dual independent screening per stage, and who may adjudicate conflicts: the owner, named editors, or any editor who is not one of the conflicting reviewers.

#### Scenario: Dual policy
- **WHEN** a protocol sets dual screening for title/abstract
- **THEN** each work needs two independent decisions at that stage

### Requirement: Exclusion reason codes
Exclusion decisions SHALL use reason codes from the protocol's list. A reason code that is not in the current protocol version SHALL be rejected. The protocol SHALL say whether title/abstract exclusions require a reason. They do not by default; full-text exclusions always do.

#### Scenario: Protocol requires title/abstract reasons
- **WHEN** a protocol requires reasons at title/abstract and a reviewer excludes a work there without one
- **THEN** the decision is rejected with `VALIDATION_ERROR`

#### Scenario: Unknown reason
- **WHEN** a reviewer excludes a work with a reason code not in the protocol
- **THEN** the decision is rejected with `VALIDATION_ERROR`

### Requirement: Review mode in the wizard
The new-project wizard SHALL include a review-mode step, which creates the first protocol version with the chosen method.

#### Scenario: Bibliometric mode
- **WHEN** a user selects bibliometric mode in the wizard
- **THEN** the project's first protocol version has method `bibliometric`

### Requirement: Protocol tab
The Protocol tab SHALL show the current protocol and its version history, and let editors create a new version.

#### Scenario: View history
- **WHEN** a user opens the Protocol tab
- **THEN** all protocol versions are listed with author and date
