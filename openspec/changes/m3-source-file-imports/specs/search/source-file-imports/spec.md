# Spec Delta: search/source-file-imports

## Purpose

Imports bibliographic export files as provenance-preserving source runs, so every source remains usable without an API. Supported exports come from Scopus, Web of Science, OpenAlex and reference managers.

## ADDED Requirements

### Requirement: Upload a source file
`POST /api/v1/projects/{project_id}/source-imports` SHALL accept a file upload from editors, owners and the administrator, with a declared source and format. It SHALL respond 202 with a background import job.

#### Scenario: Upload Scopus CSV
- **WHEN** an editor uploads a Scopus CSV export declared as source Scopus, format CSV
- **THEN** an import job starts and its status can be polled

### Requirement: Supported formats
The importer SHALL accept:
- BibTeX (`.bib`);
- RIS (`.ris`);
- Scopus CSV;
- WoS plain-text, tab-delimited and BibTeX exports;
- OpenAlex works JSON.

Other formats SHALL be rejected with `VALIDATION_ERROR`.

#### Scenario: Unsupported format
- **WHEN** a user uploads a spreadsheet file declared as RIS
- **THEN** the import is rejected before parsing records

### Requirement: File validation
The importer SHALL check, before importing records:
- size against the upload limit;
- text encoding;
- that the content matches the declared format;
- the record count against the configured maximum.

A file that fails these checks SHALL import nothing.

#### Scenario: Wrong declared format
- **WHEN** a BibTeX file is declared as WoS plain text
- **THEN** the import fails validation and no records are added

### Requirement: Per-record errors
Malformed individual records SHALL be skipped and reported with their position in the file and the reason. Well-formed records SHALL still be imported, and the counts of imported and skipped records SHALL be shown.

#### Scenario: One bad record
- **WHEN** a RIS file has 99 valid records and one record without an end tag
- **THEN** 99 records are imported and the report names the malformed record's position

### Requirement: Content safety
Imported files SHALL be treated as untrusted text. They SHALL never be executed or rendered as HTML, and binary content in a text format SHALL be rejected.

#### Scenario: Binary disguised as RIS
- **WHEN** an executable is uploaded with a `.ris` name
- **THEN** it is rejected as invalid content

### Requirement: Import provenance
Each import SHALL create a source run with:
- origin `file_import`, no query version and credential scope `none`;
- the original filename, the uploader and the file's SHA-256.

The original file SHALL be stored write-once under the project's `imports/` directory. Each record SHALL be normalised and linked to its raw entry.

#### Scenario: Import recorded
- **WHEN** an import completes
- **THEN** a source run with origin `file_import` exists, linking the stored file and its records

### Requirement: Repeated file warning
When a file with the same SHA-256 has already been imported into the project, the system SHALL warn the user, and SHALL import it again only after explicit confirmation.

#### Scenario: Same file twice
- **WHEN** an editor uploads a file identical to an earlier import
- **THEN** the upload requires confirmation before importing

### Requirement: Cited references preserved
When a Scopus or WoS export contains cited references, the importer SHALL keep them with each record.

#### Scenario: WoS export with references
- **WHEN** a WoS plain-text export with cited-reference fields is imported
- **THEN** each imported record retains its cited references

### Requirement: Imports attributed to their source
Each import's source run SHALL record the declared source provider and its retrieved count. Imported records are therefore identified records of that source, alongside API results, and search history SHALL show them that way.

#### Scenario: Import counted
- **WHEN** 200 Scopus records are imported from a file
- **THEN** the import's source run has provider Scopus with 200 retrieved records, and search history lists it under Scopus

### Requirement: Licensed-source marking
Source runs imported from Scopus or WoS files SHALL be marked as licensed content, so that exports can apply rights warnings.

#### Scenario: Scopus import marked
- **WHEN** a Scopus export is imported
- **THEN** its source run is marked as licensed content

### Requirement: Import dialog
The GUI SHALL provide an import dialog for choosing the source and format and uploading the file. It SHALL then show progress and the validation report.

#### Scenario: Import from GUI
- **WHEN** an editor imports a file through the dialog
- **THEN** the dialog shows progress and, at the end, the imported and skipped counts
