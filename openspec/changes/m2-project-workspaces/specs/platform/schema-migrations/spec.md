# Spec Delta: platform/schema-migrations

## Purpose

Evolves the catalogue and every project database safely across releases, with versioned migrations, a maintenance lock, pre-migration backups and recovery when a migration fails.

## ADDED Requirements

### Requirement: Versioned schemas
The catalogue and the project database template SHALL each have versioned migration scripts. New projects SHALL be created at the latest project schema version. Each project's schema version SHALL be recorded in the catalogue.

#### Scenario: New project version
- **WHEN** a project is created
- **THEN** its recorded schema version equals the latest project schema version

### Requirement: Migrate command
`litfoundry migrate` SHALL migrate the catalogue and then every project, one at a time, verifying each result and recording its new schema version. It SHALL report per-project outcomes and exit non-zero if any project failed.

#### Scenario: Upgrade with several projects
- **WHEN** `litfoundry migrate` runs after an upgrade on an installation with three projects
- **THEN** the catalogue and all three projects are at the latest versions and the command reports success for each

### Requirement: Maintenance lock during migration
`litfoundry migrate` SHALL hold the global maintenance lock for its whole run. While it is held, application writes SHALL be refused with 503 `MAINTENANCE_IN_PROGRESS`, and full backups, restores and other migrations SHALL NOT start.

#### Scenario: Backup during migration
- **WHEN** a full backup is requested while a migration holds the maintenance lock
- **THEN** the backup does not start and reports the lock

### Requirement: Pre-migration backup and failure recovery
Before migrating a database, `litfoundry migrate` SHALL take a consistent copy of it. If a project's migration fails, the system SHALL restore that project from its copy, leave it at its previous version and mark it unavailable until migrated. The failure SHALL be reported.

#### Scenario: Failing project migration
- **WHEN** a migration script fails on one project
- **THEN** that project's database is restored to its pre-migration state and reported as failed
- **AND** other projects remain usable

### Requirement: Schema version gate
The server and worker SHALL refuse to start when the catalogue schema is older or newer than the version the code expects, and SHALL name the corrective command. Projects at a non-current schema version SHALL be unavailable until migrated.

#### Scenario: Pending catalogue migration
- **WHEN** `litfoundry serve` starts after an upgrade without running `litfoundry migrate`
- **THEN** it exits with an error telling the operator to run `litfoundry migrate`

### Requirement: Migration status visible to the administrator
The readiness endpoint, `litfoundry status` and the admin system screen SHALL report the catalogue schema version, the number of projects at each schema version and the result of the last migration run.

#### Scenario: Status after failed migration
- **WHEN** the last migration left one project failed
- **THEN** the admin system screen lists that project as needing migration
