# Spec Delta: platform/licence-compliance

## Purpose

Keeps every LitFoundry distribution compliant with the GNU GPL v3, both for LitFoundry itself and for every bundled component, with an automated check that runs before any package is built.

## ADDED Requirements

### Requirement: Locked dependencies
The repository SHALL contain a checked-in lockfile or constraints file pinning every runtime dependency used for packaging.

#### Scenario: Unpinned dependency
- **WHEN** a packaging build finds a runtime dependency without a pinned version
- **THEN** the build fails

### Requirement: Licence inventory and SBOM
Each package build SHALL generate a licence inventory and a software bill of materials covering every bundled component, including transitive dependencies and vendored frontend files.

#### Scenario: Inventory produced
- **WHEN** a release package is built
- **THEN** its licence inventory and SBOM list every bundled component with version and licence

### Requirement: Licence gate
Before packaging, an automated check SHALL fail the build if any bundled component's licence is unknown or incompatible with GPLv3. This covers GPL-2.0-only components and licences that forbid commercial use, as well as data or model files under non-commercial terms.

#### Scenario: Incompatible component
- **WHEN** a dependency with a GPL-2.0-only licence is added
- **THEN** the licence gate fails and names the component

### Requirement: Notices and source offer
Binary distributions SHALL ship the GPLv3 text, every bundled component's licence text and notices, and an offer of the corresponding source for LitFoundry and the bundled copyleft components.

#### Scenario: Notices in package
- **WHEN** the Windows package is inspected
- **THEN** it contains the licence texts, notices and the source offer

### Requirement: Optional heavy components excluded
Optional components that pull in large machine-learning stacks SHALL NOT be bundled unless explicitly enabled in the build configuration.

#### Scenario: Default build
- **WHEN** the default release build runs
- **THEN** no optional machine-learning stack is in the package
