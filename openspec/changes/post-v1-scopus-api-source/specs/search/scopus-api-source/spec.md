# Spec Delta: search/scopus-api-source

## Purpose

Retrieves Scopus records through the Scopus Search API for institutions entitled to use it. Each job's credentials and caches are isolated, and coverage reflects what the entitlement actually returns.

## ADDED Requirements

### Requirement: Scopus API retrieval
The adapter SHALL execute the compiled Scopus query against the Scopus Search API using the requester's effective Scopus credential. It SHALL page through results and preserve raw payloads, under the common search-run rules.

#### Scenario: Scopus search
- **WHEN** an editor runs a search with the Scopus API enabled and a valid key
- **THEN** a Scopus source run retrieves records and stores raw pages

### Requirement: Per-job isolation
Each Scopus job SHALL use only its own credential and a response cache under the project's `temp/` directory. Its client configuration SHALL never be shared with another job in the same process.

#### Scenario: Concurrent Scopus jobs
- **WHEN** two users with different Scopus keys run searches at the same time
- **THEN** each job's requests carry its own key, and no cache entries are shared

### Requirement: Entitlement-aware coverage
When the entitlement level does not return abstracts or references, the affected records SHALL be flagged and the coverage reported. When entitlement limits retrieval, the run SHALL be marked `partial`.

#### Scenario: No abstract entitlement
- **WHEN** the key's entitlement omits abstracts
- **THEN** records are flagged as lacking abstracts and the run shows the coverage

### Requirement: Scopus budgets and errors
Scopus calls SHALL count against the key's budget. Provider failures SHALL map to the typed source errors, including `ACCESS_DENIED` for missing entitlement.

#### Scenario: Not entitled
- **WHEN** the key lacks Scopus Search API entitlement
- **THEN** the source run fails with `ACCESS_DENIED`

### Requirement: Licensed marking
Scopus API source runs SHALL be marked as licensed content.

#### Scenario: Export warning
- **WHEN** a project with Scopus API records is exported
- **THEN** the export requires the rights acknowledgement
