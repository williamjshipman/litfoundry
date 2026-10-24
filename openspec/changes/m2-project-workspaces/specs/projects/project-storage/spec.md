# Spec Delta: projects/project-storage

## Purpose

Keeps each project physically separate, in its own folder and SQLite database under the data root, so projects stay isolated and portable and are safe to move, back up and delete.

## ADDED Requirements

### Requirement: One folder and database per project
Each project SHALL be stored in `<data_root>/projects/<project_uuid>/`, containing:
- its own `project.sqlite`;
- `manifest.json`;
- the directories `sources/`, `imports/`, `attachments/`, `figures/`, `reports/`, `exports/` and `temp/`.

There SHALL be no shared per-user project database.

#### Scenario: Folder layout
- **WHEN** a project is created
- **THEN** its folder contains `project.sqlite`, `manifest.json` and the listed directories

### Requirement: Ownership only in the catalogue
Project folders SHALL be named only by project UUID. Ownership SHALL be recorded only in the central catalogue, so a change of owner never moves or renames files.

#### Scenario: Folder name independent of owner
- **WHEN** a project's ownership is transferred
- **THEN** its folder name and contents are unchanged

### Requirement: Project manifest
`manifest.json` SHALL record the product identifier, the project UUID and the project schema version. It SHALL contain no secrets and no absolute host paths.

#### Scenario: Manifest content
- **WHEN** a project's manifest is read
- **THEN** it contains `product`, project UUID and schema version and no absolute path

### Requirement: Project isolation
Every project request SHALL resolve the project UUID through the catalogue, authorise the caller, then open only that project's database. A request SHALL never read or write another project's data, whatever UUIDs or paths it supplies.

#### Scenario: Forged project UUID
- **WHEN** a user requests a record using their own project's URL but another project's record ID
- **THEN** the record is not found and no data from the other project is returned

### Requirement: No idle database handles
Project database connections SHALL be closed when each operation ends, so a project folder can be moved or deleted immediately after use, including on Windows.

#### Scenario: Delete right after use
- **WHEN** a project is deleted on Windows moments after another process read from it
- **THEN** the folder is moved to `trash/` without a file-in-use error

### Requirement: Write-once project files
Persistent project files SHALL be written to a temporary name, flushed and atomically renamed into place, and SHALL never be modified afterwards. Persistent project files include raw source payloads, imports, attachments, figures, reports and artifacts. Only housekeeping SHALL remove them.

#### Scenario: Interrupted write
- **WHEN** the process is killed while writing a project file
- **THEN** no partially written file exists under its final name

### Requirement: Files in place before references
A database row that references a project file SHALL be committed only after that file is in place under its final name. Any database snapshot therefore references only files that exist.

#### Scenario: Snapshot during upload
- **WHEN** a database snapshot is taken while an attachment upload is in progress
- **THEN** the snapshot either does not reference the attachment, or the attachment file already exists under its final name

### Requirement: Cross-database reconciliation
Workflows that touch both the catalogue and a project database SHALL record explicit workflow states and idempotency keys. `litfoundry reconcile` SHALL detect and repair the following inconsistencies, and report each action:
- `provisioning` rows without folders;
- project folders without catalogue rows;
- projects stuck in `deleting`.

#### Scenario: Orphan provisioning row
- **WHEN** the process crashed during provisioning and `litfoundry reconcile` runs
- **THEN** the orphan catalogue row and any staging folder are removed and the action is reported
