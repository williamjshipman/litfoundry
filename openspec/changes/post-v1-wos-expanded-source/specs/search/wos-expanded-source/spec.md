# Spec Delta: search/wos-expanded-source

## Purpose

Retrieves full Web of Science records, including abstracts, cited references and addresses, through the WoS API Expanded, for institutions with that entitlement.

## ADDED Requirements

### Requirement: Expanded API retrieval
The adapter SHALL execute the compiled `TS=` query, using the Expanded field tag set, against the configured, versioned WoS API Expanded endpoint with the requester's effective credential. It SHALL page through all results under the common search-run rules. It SHALL never use the retired WoS Lite API.

#### Scenario: Expanded search
- **WHEN** an editor runs a search with WoS Expanded enabled and an entitled key
- **THEN** full records are retrieved and raw pages stored

### Requirement: Entitlement validation
Credential validation SHALL confirm Expanded entitlement. A key without it SHALL fail validation, and searches with it SHALL fail with `ACCESS_DENIED`.

#### Scenario: Starter-only key
- **WHEN** a Starter-only key is used for WoS Expanded
- **THEN** validation reports the missing entitlement

### Requirement: Full-record normalisation
Expanded records SHALL be normalised with abstracts, cited references, Keywords Plus, author addresses, affiliations and countries, in addition to the basic metadata.

#### Scenario: References available
- **WHEN** an Expanded record with cited references is normalised
- **THEN** its cited references are stored for citation analyses

### Requirement: Budgets, errors and licensing
Expanded calls SHALL count against the key's budget, map failures to typed source errors and mark runs `partial` when retrieval is incomplete. Expanded source runs SHALL be marked as licensed content.

#### Scenario: Licensed export
- **WHEN** a project with WoS Expanded records is exported
- **THEN** the export requires the rights acknowledgement
