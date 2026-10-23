# Spec Delta: data/project-import

## Purpose

Imports a previously exported project archive as a new, private project owned by the importer. The archive is treated as untrusted input, and the original provenance is preserved.

## ADDED Requirements

### Requirement: Import an archive
`POST /api/v1/project-imports` SHALL let an authenticated user upload a project archive, responding 202 with an import job. The result SHALL be a new project owned by the caller.

#### Scenario: Import own export
- **WHEN** a user imports an archive exported from another installation
- **THEN** a new project owned by that user appears in their project list

### Requirement: Untrusted archive validation
Before extracting, the importer SHALL validate:
- total size, entry count and entry types;
- paths, rejecting absolute paths, `..` and symbolic links;
- compression ratios, to reject compression bombs;
- the manifest's product identifier and format version;
- the checksums of every file.

Any failure SHALL abort the import without changes.

#### Scenario: Path traversal
- **WHEN** an archive contains an entry named `../../catalog.sqlite`
- **THEN** the import is rejected and nothing is written outside staging

#### Scenario: Zip bomb
- **WHEN** an archive's entries expand beyond the configured ratio or size quota
- **THEN** the import is rejected during validation

#### Scenario: Wrong product
- **WHEN** an archive's manifest does not identify `litfoundry`
- **THEN** the import is rejected before extraction

### Requirement: Quota-limited staging
Extraction SHALL happen in a staging directory with a size quota, outside the live project folders.

#### Scenario: Staging cleaned
- **WHEN** an import fails during extraction
- **THEN** the staging directory is removed and no project is registered

### Requirement: Schema compatibility
An archive whose project schema is older than the installation's SHALL be migrated in staging. One whose schema is newer SHALL be rejected with an explanation.

#### Scenario: Newer archive
- **WHEN** an archive was exported by a newer LitFoundry with a newer project schema
- **THEN** the import is rejected, naming the versions

### Requirement: Rekeyed private project
The imported project SHALL:
- get a new project UUID;
- be owned by the importer;
- have private visibility and no ACL entries;
- have no job leases or queued jobs;
- have no credentials.

#### Scenario: Shared project imported
- **WHEN** a project that was Public edit with ACL entries is imported
- **THEN** the new project is private with no ACL entries

### Requirement: Preserved people and provenance
Reviewer and actor IDs SHALL be kept unchanged. People who match no account on this installation SHALL be kept as non-login provenance entries marked `imported`. The original project UUID, export time and source installation SHALL be recorded in imported-from fields.

#### Scenario: Unknown reviewer
- **WHEN** an imported project's decisions were made by a reviewer who has no account here
- **THEN** the decisions show that reviewer, marked as imported, and that person cannot sign in

### Requirement: Never overwrite
An import SHALL always create a new project and SHALL never overwrite an existing one, even if the original project UUID exists on this installation.

#### Scenario: Re-import on same installation
- **WHEN** a user imports an export of a project that still exists here
- **THEN** a second, separate project is created

### Requirement: Atomic registration
The imported project SHALL be registered in the catalogue only after validation, extraction and migration succeed. The registration SHALL be atomic, so a failure leaves no partial project.

#### Scenario: Crash during import
- **WHEN** the worker crashes before registration
- **THEN** no catalogue entry exists and reconciliation removes the staging data

### Requirement: Round-trip fidelity
An export followed by an import SHALL preserve:
- the schema;
- file checksums;
- corpus hashes and corpus snapshot hashes;
- artifacts;
- screening ledgers;
- reviewer identities.

#### Scenario: Round trip
- **WHEN** a project is exported and imported
- **THEN** every corpus hash and artifact checksum in the new project equals the original
