# Spec Delta: review/corpus-snapshots

## Purpose

Freezes the set of included works and studies, together with the inputs that produced it, into an immutable, hashed corpus version. Analyses and PRISMA reports then always refer to exactly reproducible data.

## ADDED Requirements

### Requirement: Freeze a corpus
`POST /api/v1/projects/{project_id}/corpora` SHALL let editors freeze a corpus with a label, a protocol version and the selected search runs. `GET` SHALL list corpus versions to users with read access.

#### Scenario: Freeze
- **WHEN** an editor freezes a corpus from two search runs under protocol version 3
- **THEN** a frozen corpus with its members, inputs and hash is created

### Requirement: Membership rules
Corpus members SHALL be determined by the protocol method:
- **Systematic and scoping reviews:** the canonical works whose final decision at the last conducted stage is `include`, with their study links.
- **Bibliometric reviews:** all canonical, unmerged works from the selected search runs.

#### Scenario: Systematic membership
- **WHEN** a systematic-review corpus is frozen
- **THEN** only works finally included at the last conducted stage are members

#### Scenario: Bibliometric membership
- **WHEN** a bibliometric corpus is frozen without screening
- **THEN** all unmerged works from the selected runs are members

### Requirement: Frozen contents
A frozen corpus SHALL record:
- its member work and study IDs;
- the selected search runs;
- the protocol version;
- a snapshot of the full screening-resolution ledger used;
- the creator and time.

A frozen corpus SHALL never change.

#### Scenario: Screening changes after freeze
- **WHEN** a reviewer changes a decision after a corpus was frozen
- **THEN** the frozen corpus's members and ledger snapshot are unchanged

### Requirement: Frozen member metadata
Freezing a corpus SHALL also snapshot the canonical metadata of every member work as it stands at that moment, covering every field analyses and reports use. That includes titles, abstracts, dates, sources, authors, affiliations, keywords, cited references and per-source citation counts with their dates. Later edits, merges or canonicalisation SHALL NOT change the snapshot.

#### Scenario: Title edited after freeze
- **WHEN** an editor corrects a member work's title after the corpus was frozen
- **THEN** the corpus's metadata snapshot still holds the title as it was at freeze time

### Requirement: Frozen PRISMA inputs
Freezing a corpus SHALL snapshot every input the PRISMA counts need, as it stands at that moment:
- the identified records per source run;
- the duplicate merges;
- the screening decisions and resolutions;
- the retrieval attempts;
- the full-text reports and study links.

#### Scenario: Retrieval recorded after freeze
- **WHEN** an editor records a new retrieval attempt after the corpus was frozen
- **THEN** the corpus's frozen PRISMA inputs do not include it

### Requirement: Snapshot hash
Each corpus SHALL record a SHA-256 over a canonical serialisation of its frozen metadata and PRISMA inputs, separate from the corpus hash, so any change to the frozen data is detectable.

#### Scenario: Snapshot integrity
- **WHEN** a corpus's frozen data is verified
- **THEN** its recomputed snapshot hash equals the recorded one

### Requirement: Corpus hash
Each corpus SHALL have a SHA-256 hash over a canonical serialisation of its sorted member IDs, protocol version ID and selected search-run IDs. The hash SHALL exclude the project UUID, so it survives export and import.

#### Scenario: Hash after import
- **WHEN** a project is exported and imported as a new project
- **THEN** each corpus's hash is unchanged

### Requirement: Partial source acknowledgement
Freezing a corpus whose selected search runs include a `partial` source run SHALL require an explicit acknowledgement. The acknowledgement SHALL be recorded with the corpus.

#### Scenario: Partial run without acknowledgement
- **WHEN** an editor freezes a corpus including a partial run without acknowledging it
- **THEN** the request fails with `VALIDATION_ERROR` naming the partial run

### Requirement: New versions for changes
Any change in members or inputs SHALL require freezing a new corpus version. Analyses and PRISMA snapshots SHALL keep referring to the version they used.

#### Scenario: New version
- **WHEN** an editor freezes again after more screening
- **THEN** a new corpus version exists and earlier analyses still reference the old one

### Requirement: Merged members remain resolvable
Corpus members that are later merged into other works SHALL still resolve through their merge pointers. The frozen membership SHALL stay unchanged.

#### Scenario: Member merged later
- **WHEN** a member work is merged into another after freezing
- **THEN** the corpus lists the original ID, resolvable to the retained work
