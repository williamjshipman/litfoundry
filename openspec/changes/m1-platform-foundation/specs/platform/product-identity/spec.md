# Spec Delta: platform/product-identity

## Purpose

Fixes the LitFoundry product name, tagline, description and machine identifiers, so users, operators and tooling see one consistent product everywhere.

## ADDED Requirements

### Requirement: Product name and tagline in the GUI
The GUI SHALL show the product name `LitFoundry`, with exactly that capitalisation, and the tagline *From literature to insight.* in the application header, the sign-in and setup pages, the administrator console and the About screen. Every page's HTML title SHALL contain `LitFoundry`.

#### Scenario: Branded sign-in page
- **WHEN** a browser opens the sign-in page
- **THEN** the page shows `LitFoundry` and the tagline
- **AND** the document title contains `LitFoundry`

#### Scenario: Branded application header
- **WHEN** a signed-in user opens any application page
- **THEN** the header shows `LitFoundry`

### Requirement: Product description
The About screen, documentation and installer SHALL describe the product as "Open-source software for systematic literature reviews, PRISMA workflows and bibliometric analysis."

#### Scenario: Description on About screen
- **WHEN** a signed-in user opens the About screen
- **THEN** the product description is shown verbatim

### Requirement: Machine identifier
The Python distribution, the import package and the command-line executable SHALL all be named `litfoundry`. The command-line executable SHALL report the LitFoundry version.

#### Scenario: Installed CLI and package
- **WHEN** the package is installed into a clean virtual environment with `pip install -e .`
- **THEN** `import litfoundry` succeeds
- **AND** `litfoundry --version` prints the LitFoundry version

### Requirement: Configuration environment prefix
Every configuration environment variable SHALL use the `LITFOUNDRY_` prefix, including `LITFOUNDRY_DATA_ROOT`. A configuration reference SHALL document every variable, its default and its platform-specific values for Windows, Linux and macOS.

#### Scenario: Data root from the environment
- **WHEN** `LITFOUNDRY_DATA_ROOT` is set to a directory and `litfoundry init` runs
- **THEN** the data root is created in that directory

#### Scenario: Unprefixed variables are ignored
- **WHEN** a configuration value is supplied only through a variable without the `LITFOUNDRY_` prefix
- **THEN** LitFoundry does not read it

### Requirement: Process names
The server and worker processes SHALL identify themselves as `litfoundry-server` and `litfoundry-worker` in log entries and status output.

#### Scenario: Process name in logs
- **WHEN** the server process writes a log entry
- **THEN** the entry identifies the process as `litfoundry-server`

### Requirement: Legacy identifiers are not introduced
The system SHALL NOT create packages, commands, services, files, directories or configuration keys named `brm`, `pybrm`, `bibliometric-research-manager` or `appctl`.

#### Scenario: Repository naming check
- **WHEN** the naming test scans the source tree, packaging scripts and the installed entry points
- **THEN** none of the forbidden identifiers is found

### Requirement: About screen
The About screen SHALL show the product name, tagline, version, licence (GNU GPL v3) and the administrator trust disclosure: the administrator can read and change every project and, through the server host and full backups, all stored data and credentials.

#### Scenario: Trust disclosure shown
- **WHEN** any signed-in user opens the About screen
- **THEN** the licence and the administrator trust disclosure are shown
