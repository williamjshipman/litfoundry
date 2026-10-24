# Spec Delta: review/screening

## Purpose

Supports PRISMA-guided screening with independent reviewer decisions, recorded conflicts and resolutions, and auditable final decisions per work and stage.

## ADDED Requirements

### Requirement: Screening rounds
Screening SHALL be organised in rounds per stage (`title_abstract` or `full_text`). Each round records the reviewer policy in force and its start and close times. Decisions SHALL be accepted only in an open round.

#### Scenario: Closed round
- **WHEN** a reviewer submits a decision to a closed round
- **THEN** the decision is rejected with `CONFLICT`

### Requirement: Reviewer decisions
`POST /api/v1/projects/{project_id}/screening/decisions` SHALL let editors, owners and the administrator record a decision for a work and stage. A decision is `include`, `exclude` or `uncertain`, with optional notes and reason codes. A reason code SHALL be required for `exclude` at the full-text stage. At the title/abstract stage, it SHALL be required only when the protocol says so. `GET` SHALL return decisions visible to the caller.

#### Scenario: Title/abstract exclude without reason
- **WHEN** a reviewer excludes a work at title/abstract without a reason code, under a protocol that does not require one
- **THEN** the decision is accepted

#### Scenario: Full-text exclude without reason
- **WHEN** a reviewer excludes a work at the full-text stage without a reason code
- **THEN** the decision is rejected with `VALIDATION_ERROR`

#### Scenario: Viewer cannot screen
- **WHEN** a viewer submits a decision
- **THEN** the response is 403

### Requirement: Append-only decision history
Each decision SHALL be an append-only event with a version number. Changing a decision SHALL add a new version, and earlier versions SHALL stay visible in the history.

#### Scenario: Changed mind
- **WHEN** a reviewer changes a decision from exclude to include
- **THEN** both versions exist in the work's decision history

### Requirement: Independent dual screening
Under dual screening, a reviewer SHALL NOT see other reviewers' decisions on a work until they have recorded their own. Adjudicators SHALL see all decisions.

#### Scenario: Blinded second reviewer
- **WHEN** reviewer A has decided and reviewer B opens the same work
- **THEN** reviewer B does not see reviewer A's decision

### Requirement: Conflict detection
Under dual screening, a work SHALL be flagged as conflicted when its reviewers' latest decisions differ, or when any of them is `uncertain`.

#### Scenario: Disagreement
- **WHEN** reviewer A includes and reviewer B excludes a work
- **THEN** the work is flagged as conflicted at that stage

### Requirement: Resolutions
`POST /api/v1/projects/{project_id}/screening/resolutions` SHALL let an eligible adjudicator record a final decision for a conflicted work and stage, with a reason code and the adjudicator's identity. Adjudicators who were among the conflicting reviewers SHALL be refused unless the policy allows it.

#### Scenario: Adjudicate
- **WHEN** an eligible adjudicator resolves a conflict as exclude with a reason
- **THEN** a resolution record is stored and the work's final decision is exclude

### Requirement: Final decision derivation
A work's final decision at a stage SHALL be:
- **single screening:** the reviewer's latest decision;
- **dual screening, agreeing reviewers:** the agreed decision;
- **dual screening, conflicted:** the resolution.

Until then the work SHALL count as unresolved. Every final decision SHALL be traceable to its decision or resolution events.

#### Scenario: Unresolved conflict
- **WHEN** a conflicted work has no resolution
- **THEN** it counts as unresolved and is excluded from neither the included nor the excluded totals

### Requirement: Decisions follow merges
Screening decisions SHALL stay attached to the work IDs they were made on. Decisions on works merged into a retained work SHALL be shown on the retained work, and SHALL count once for it.

#### Scenario: Merged after screening
- **WHEN** two screened works are merged
- **THEN** both decision histories appear on the retained work and it is counted once

### Requirement: Concurrency on decisions
Decision submissions SHALL use optimistic concurrency on the work's screening state. They SHALL be refused with 409 `RECORD_LOCKED` while a running `records`-scope job holds the work.

#### Scenario: During merge
- **WHEN** a reviewer screens a work held by a running merge job
- **THEN** the response is 409 `RECORD_LOCKED`

### Requirement: Screening queue
Each reviewer's queue SHALL list the works awaiting their decision at the stage. It SHALL exclude works merged into others, and flag works without an abstract.

#### Scenario: Missing abstract flagged
- **WHEN** a WoS Starter work without an abstract enters the queue
- **THEN** it is flagged as having no abstract

### Requirement: Bulk decisions
Editors SHALL be able to apply one decision with a reason code to a selected set of works. This SHALL run as a `records`-scope job, recording an individual decision event per work.

#### Scenario: Bulk exclude
- **WHEN** an editor bulk-excludes 50 selected works with a reason
- **THEN** 50 decision events are recorded by one job

### Requirement: Screening screen
The screening screens SHALL:
- offer keyboard shortcuts for include, exclude, uncertain, next and previous;
- show exclusion reasons and notes;
- show progress and per-stage counts (screened, included, excluded, uncertain, conflicts, remaining), overall and per reviewer;
- give access to reconciliation for adjudicators.

#### Scenario: Keyboard screening
- **WHEN** a reviewer presses the include shortcut
- **THEN** the decision is recorded and the next work opens
