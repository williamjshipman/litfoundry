# Spec Delta: search/search-strategy

## Purpose

Captures a project's keyword search strategy as a validated, source-independent Boolean structure that users can edit and that is versioned immutably each time it is used.

## ADDED Requirements

### Requirement: Canonical strategy structure
A strategy SHALL consist of:
- an AST, whose Boolean nodes carry `op` (`and`, `or` or `not`) and `children`, and whose leaves carry `type` (`term` or `phrase`), `value` and optional flags such as `wildcard`;
- a scope, holding the fields, a year range, document types and languages.

A `not` node SHALL have exactly one child, and SHALL appear only as a child of an `and` node.

#### Scenario: NOT at the root
- **WHEN** a strategy whose root node is `not` is saved
- **THEN** it is rejected with `VALIDATION_ERROR`

#### Scenario: Valid nested strategy
- **WHEN** a strategy ANDs two OR groups and a NOT group with one child
- **THEN** it is accepted

### Requirement: Published grammar
The project SHALL publish the strategy grammar as a JSON Schema at `docs/query-ast.schema.json`. Every stored strategy SHALL be validated against it. Validation errors SHALL identify the offending node path.

#### Scenario: Invalid leaf
- **WHEN** a leaf has `type` `regex`
- **THEN** saving fails with `VALIDATION_ERROR` naming the leaf's path

### Requirement: Safe term values
Term and phrase values SHALL be able to contain quotes, backslashes and characters that are special in source query languages. They SHALL be stored verbatim and escaped only during compilation.

#### Scenario: Embedded quote
- **WHEN** a phrase value contains a double quote
- **THEN** it is stored unchanged and every compiled query escapes it correctly

### Requirement: Editable draft
`GET` and `PUT /api/v1/projects/{project_id}/search-strategy` SHALL read and replace the project's current draft strategy. Updates SHALL require `If-Match`. Only editors, owners and the administrator SHALL be able to update it.

#### Scenario: Concurrent edits
- **WHEN** two editors save the draft from the same revision
- **THEN** the second save fails with 409 `CONFLICT`

### Requirement: Immutable strategy versions
Each time a search runs, the system SHALL record an immutable strategy version holding:
- the AST and scope;
- a rationale;
- the creator;
- the timestamp.

The search run SHALL reference this version. Later draft edits SHALL never change a recorded version.

#### Scenario: Edit after search
- **WHEN** an editor changes the draft after a search ran
- **THEN** the earlier search run still shows the strategy it actually used

### Requirement: Source selection
Each project SHALL record, per provider (Scopus, Web of Science, OpenAlex), whether the source is enabled, along with source-specific options. Editors SHALL change these with switches in the search editor.

#### Scenario: Disable a source
- **WHEN** an editor disables Scopus
- **THEN** Scopus is excluded from query previews and search runs

### Requirement: Strategy editor
The search editor SHALL let editors:
- build groups of terms and phrases (OR within a group, AND between groups);
- nest AND, OR and NOT groups;
- add synonyms and an exclusion group;
- quote phrases;
- set a year range, document types, languages and an optional subject scope.

It SHALL also show validation and credential status per source.

#### Scenario: Build a strategy
- **WHEN** an editor adds two concept groups and an exclusion term in the editor
- **THEN** the saved AST has an `and` root with two `or` groups and a `not` child

### Requirement: Strategy step in the new project wizard
The new-project wizard SHALL include an optional strategy step for keywords, the date range, document types and selected sources. This step SHALL save the project's first draft strategy.

#### Scenario: Wizard strategy
- **WHEN** a user enters keywords and selects OpenAlex in the wizard
- **THEN** the new project's draft strategy and source selection reflect those choices
