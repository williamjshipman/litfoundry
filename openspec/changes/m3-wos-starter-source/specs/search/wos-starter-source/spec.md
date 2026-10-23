# Spec Delta: search/wos-starter-source

## Purpose

Retrieves Web of Science records through the Clarivate WoS Starter API within the key's quota. Missing fields are enriched from OpenAlex where possible, and the remaining gaps are flagged so users are not misled about coverage.

## ADDED Requirements

### Requirement: Starter API requests
The adapter SHALL query the WoS Starter documents endpoint over HTTPS, with `db=WOS`, the compiled `q` expression and the effective key in the `X-ApiKey` header. It SHALL use page-number paging with at most 50 records per page. It SHALL never call the retired WoS Lite API.

#### Scenario: Paged retrieval
- **WHEN** a query reports 120 results
- **THEN** the adapter requests 3 pages of up to 50 records, with the key only in the `X-ApiKey` header

### Requirement: Key required
A WoS Starter search or count SHALL fail with `AUTH_REQUIRED`, without any request, when no effective WoS Starter credential exists.

#### Scenario: No WoS key
- **WHEN** a search runs with WoS Starter enabled and no effective key
- **THEN** the WoS source run fails with `AUTH_REQUIRED` and OpenAlex results are unaffected

### Requirement: Quota accounting
Every Starter request SHALL count against the key's daily budget. A quota rejection from the provider SHALL stop retrieval for that key, keep the records already retrieved and mark the run `partial`.

#### Scenario: Provider quota reached
- **WHEN** the provider rejects a request because the daily quota is used up
- **THEN** the source run is `partial`, the stored records remain and the error is reported

### Requirement: Paging limit makes run partial
If the API cannot page through all reported results, the source run SHALL be marked `partial`, with retrieved and reported counts and an explanation.

#### Scenario: Results beyond the retrievable limit
- **WHEN** the reported count exceeds what the API lets the adapter page through
- **THEN** the run is `partial` and the explanation names the provider limit

### Requirement: Starter normalisation
Each Starter record SHALL be normalised into:
- UT and DOI, ISSN and PMID identifiers;
- title, document type and source details;
- authors and author keywords;
- times cited, with its retrieval date.

The record SHALL be marked as lacking an abstract, cited references, Keywords Plus and author addresses.

#### Scenario: Normalised Starter record
- **WHEN** a Starter record with a DOI is normalised
- **THEN** it has the listed fields and its missing-field flags set

### Requirement: DOI enrichment from OpenAlex
After retrieval, Starter records with DOIs SHALL be enriched with batched OpenAlex DOI lookups, using the requester's effective OpenAlex credential and budget. Enriched fields SHALL be attributed to OpenAlex at field level. If no OpenAlex credential is available, enrichment SHALL be skipped with a warning on the run.

#### Scenario: Abstract enriched
- **WHEN** a Starter record's DOI matches an OpenAlex work with an abstract
- **THEN** the record gains the abstract, attributed to OpenAlex, and the Starter fields remain attributed to WoS

#### Scenario: No OpenAlex key
- **WHEN** no OpenAlex credential is available for the requester
- **THEN** enrichment is skipped and the WoS run shows an enrichment warning

### Requirement: Coverage flags
Records still lacking an abstract after enrichment SHALL be flagged in the screening queue. Search results SHALL report the share of Starter records lacking references, affiliations or countries, and point users to WoS export files for full records.

#### Scenario: Coverage summary
- **WHEN** a user views a completed WoS Starter run
- **THEN** it shows how many records lack abstracts, references and affiliations, and how to import WoS export files
