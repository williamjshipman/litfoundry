# Spec Delta: records/keyword-normalisation

## Purpose

Lets a project normalise keyword variants (synonyms, spelling and stop terms) through a versioned rule dictionary, so keyword analyses are consistent and reproducible.

## ADDED Requirements

### Requirement: Keyword rules
`GET` and `PUT /api/v1/projects/{project_id}/keyword-rules` SHALL read and replace the project's keyword normalisation rules. Each rule has a pattern, a replacement, a rule type and an enabled flag. The rule types are:
- `exact`, matched case-insensitively;
- `wildcard`, with a trailing `*` only;
- `stopword`.

Updates SHALL require `If-Match` and edit rights.

#### Scenario: Synonym rule
- **WHEN** an editor adds an `exact` rule mapping "machine-learning" to "machine learning"
- **THEN** keyword views and analyses treat both as "machine learning"

#### Scenario: Viewer cannot edit
- **WHEN** a viewer tries to change keyword rules
- **THEN** the response is 403

### Requirement: Source keywords unchanged
Normalisation SHALL apply to keyword views and analyses only. The stored source and canonical keywords SHALL keep their original values.

#### Scenario: Original kept
- **WHEN** a rule maps a keyword to another form
- **THEN** the work's stored keywords still show the original form

### Requirement: Versioned dictionary
Each change to the rules SHALL produce a new, immutable dictionary revision, and earlier revisions SHALL remain retrievable. Analyses SHALL record the dictionary revision they used.

#### Scenario: Analysis records dictionary
- **WHEN** a keyword analysis runs after the rules change to revision 4
- **THEN** the analysis records keyword dictionary revision 4

#### Scenario: Earlier revision retrievable
- **WHEN** the rules have moved on to revision 6
- **THEN** the rules of revision 4 can still be retrieved unchanged

### Requirement: Rule validation
Rules SHALL be validated on save. Rules with empty patterns, unsupported types, wildcards anywhere other than the end, or cycles between replacements SHALL be rejected with `VALIDATION_ERROR`.

#### Scenario: Cyclic rules
- **WHEN** rules map "a" to "b" and "b" to "a"
- **THEN** saving fails with `VALIDATION_ERROR`

### Requirement: Keyword rules screen
The project SHALL provide a keyword-rules screen. It SHALL list rules and show each rule's matching keywords and their frequency before saving.

#### Scenario: Preview matches
- **WHEN** an editor types a wildcard rule `flotat*`
- **THEN** the screen previews the keywords it would normalise
