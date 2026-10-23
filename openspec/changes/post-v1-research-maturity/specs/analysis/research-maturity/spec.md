# Spec Delta: analysis/research-maturity

## Purpose

Records reviewers' judgements of each study's validation maturity and summarises them in a review table. The categories are presented as human annotations, never as automatic conclusions.

## ADDED Requirements

### Requirement: Maturity categories
Reviewers with edit rights SHALL be able to label a corpus work with one of these categories:
- theoretical;
- simulation;
- historic data;
- pilot;
- industrial advisory;
- closed-loop;
- sustained industrial use.

Each label SHALL record the reviewer, time and notes.

#### Scenario: Label a work
- **WHEN** a reviewer labels a work as pilot, with a note
- **THEN** the label is stored with the reviewer, time and note

### Requirement: Labels are annotations only
The system SHALL never assign maturity categories automatically. The table and reports SHALL describe them as human annotations.

#### Scenario: Unlabelled works
- **WHEN** a corpus has works without labels
- **THEN** they are reported as unlabelled, not assigned a category

### Requirement: Maturity review table
The system SHALL provide a research maturity review table (analysis 10), summarising labelled works by category and by publication year, and reporting the unlabelled share. It SHALL be recorded with the usual analysis provenance.

#### Scenario: Table output
- **WHEN** analysis 10 runs on a corpus where 60% of works are labelled
- **THEN** the table shows counts per category and year, and states that 40% are unlabelled

### Requirement: Label history
Label changes SHALL be append-only. The current label SHALL be the latest, and earlier labels SHALL remain visible.

#### Scenario: Relabel
- **WHEN** a reviewer changes a label from pilot to closed-loop
- **THEN** both labels appear in the work's label history
