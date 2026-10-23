# Spec Delta: platform/data-root

## Purpose

Defines where LitFoundry keeps its persistent data, how the data root is laid out and initialised, and how it is protected on disk.

## ADDED Requirements

### Requirement: Default data root per platform
Without `LITFOUNDRY_DATA_ROOT`, the data root SHALL default as follows:
- **Windows service mode:** `%PROGRAMDATA%\LitFoundry`
- **Linux:** `/var/lib/litfoundry`
- **macOS system-wide mode:** `/Library/Application Support/LitFoundry`

Documented user-scoped locations SHALL apply to non-service development use.

#### Scenario: Windows service default
- **WHEN** `litfoundry init` runs for Windows service mode without `LITFOUNDRY_DATA_ROOT`
- **THEN** the data root is created at `%PROGRAMDATA%\LitFoundry`

#### Scenario: Override wins
- **WHEN** `LITFOUNDRY_DATA_ROOT` is set
- **THEN** that directory is used on every platform

### Requirement: Data root initialisation
`litfoundry init` SHALL create the data root layout:
- the central `catalog.sqlite`;
- the directories `secret_material/`, `projects/`, `trash/`, `logs/` and `backup_staging/`.

Running it again on an initialised data root SHALL leave existing data unchanged.

#### Scenario: Fresh initialisation
- **WHEN** `litfoundry init` runs against an empty directory
- **THEN** the catalogue database and all layout directories exist
- **AND** the catalogue is at the latest schema version

#### Scenario: Repeated initialisation
- **WHEN** `litfoundry init` runs against an initialised data root
- **THEN** no existing file is overwritten and the command reports that the data root is already initialised

### Requirement: Restrictive data root permissions
`litfoundry init` and the installers SHALL restrict the data root to the service identity and host administrators:
- **Windows:** an explicit ACL with inheritance disabled, never relying on inherited `%PROGRAMDATA%` permissions;
- **Linux and macOS:** a dedicated owner and mode `0700`.

#### Scenario: Windows ACL
- **WHEN** `litfoundry init` creates a data root on Windows
- **THEN** the data root ACL grants access only to the service identity and Administrators
- **AND** ACL inheritance is disabled

#### Scenario: POSIX mode
- **WHEN** `litfoundry init` creates a data root on Linux or macOS
- **THEN** the data root has mode `0700`

### Requirement: Local disk for live databases
LitFoundry SHALL refuse to initialise or serve from a data root that is a UNC or other network path, or that is detected to be on a network filesystem. The documentation SHALL warn against cloud-sync folders.

#### Scenario: UNC data root refused
- **WHEN** `LITFOUNDRY_DATA_ROOT` is `\server\share\litfoundry`
- **THEN** `litfoundry init` and `litfoundry serve` exit with an error explaining that live databases must be on a local disk

### Requirement: Path containment
Every file the application reads or writes on behalf of a request or job SHALL resolve to a location inside the data root. Paths containing `..`, absolute paths taken from user input, and symbolic links that resolve outside the data root SHALL be refused. The only exceptions are administrator-configured full-backup destinations and full-restore staging, which follow the full-backup and full-restore rules.

#### Scenario: Traversal refused
- **WHEN** an operation is asked to read a relative path containing `..` that would leave the data root
- **THEN** the operation is refused and nothing is read

#### Scenario: Backup destination outside the data root
- **WHEN** the administrator configures a full-backup destination outside the data root
- **THEN** the backup writes there under the full-backup rules, and no other operation may use that path

#### Scenario: Escaping symlink refused
- **WHEN** a file inside the data root is a symbolic link to a location outside it
- **THEN** the application refuses to follow it

### Requirement: User titles are metadata only
Directory and file names inside the data root SHALL be generated from UUIDs or fixed names, never from user-supplied titles or filenames.

#### Scenario: Hostile title
- **WHEN** a user names an object `../../etc`
- **THEN** no directory or file name contains that text
