# Spec Delta: search/openalex-source

## Purpose

Retrieves works from OpenAlex reliably and economically. The source respects key requirements and metered usage, reports honest counts for split queries, and normalises records for screening and bibliometrics.

## ADDED Requirements

### Requirement: Authenticated requests
OpenAlex requests SHALL go over HTTPS to the configured OpenAlex API host, with the effective API key in an `Authorization: Bearer` header. The key SHALL never appear in a URL.

#### Scenario: Key in header
- **WHEN** an OpenAlex request is sent
- **THEN** the key is in the `Authorization` header and absent from the URL and from `executed_request_json`

### Requirement: Key required
An OpenAlex search or count SHALL fail with `AUTH_REQUIRED` before any request when no effective OpenAlex credential exists.

#### Scenario: No key configured
- **WHEN** a user without a personal key runs an OpenAlex search and no shared key exists
- **THEN** the source run fails with `AUTH_REQUIRED` and no request is sent

### Requirement: Cursor retrieval
The adapter SHALL retrieve every result page using cursor pagination at the maximum supported page size, with publication-date, document-type and language filters applied as compiled. It SHALL save the cursor at each checkpoint.

#### Scenario: Multi-page result
- **WHEN** a query reports 450 results
- **THEN** all 450 records are retrieved across successive cursor pages

### Requirement: Cost recording
The adapter SHALL record each response's cost from the `X-RateLimit-Credits-Used` header against the key's budget. When the header is absent, it SHALL charge the documented default cost for the call type.

#### Scenario: Search versus filter cost
- **WHEN** a search call and a filter-only call are made
- **THEN** each records the cost reported by its response

### Requirement: Rate-limit compliance
The adapter SHALL stay within OpenAlex's documented request rate, and SHALL treat 429 responses as retryable with backoff.

#### Scenario: Burst throttled
- **WHEN** the runner retrieves many pages quickly
- **THEN** requests are spaced to stay within the documented rate

### Requirement: Split-query union counts
For a query compiled into sub-queries, the adapter SHALL run every sub-query and store the union de-duplicated by OpenAlex ID. It SHALL set `reported_count` to the size of the de-duplicated union, never to the sum of the sub-query counts.

#### Scenario: Overlapping sub-queries
- **WHEN** two sub-queries return 300 and 250 works, 50 of which overlap
- **THEN** the source run stores 500 distinct works and reports 500

### Requirement: Normalisation
The adapter SHALL normalise each work into:
- identifiers (OpenAlex ID, DOI and others);
- title, abstract (reconstructed from the inverted index), year, date, venue, type and language;
- authors with institutions and countries;
- keywords and topics;
- referenced work IDs;
- the citation count with its retrieval date.

Works lacking an abstract or references SHALL be flagged.

#### Scenario: Abstract reconstructed
- **WHEN** a work has an abstract inverted index
- **THEN** the normalised record contains the reconstructed abstract text

#### Scenario: No references
- **WHEN** a work has no referenced works
- **THEN** the normalised record is flagged as lacking references

### Requirement: Batched DOI lookup
The adapter SHALL look up works by DOI in batches, using DOI filter requests under the same credential and budget rules. Unmatched DOIs SHALL be reported.

#### Scenario: Enrich by DOI
- **WHEN** 120 DOIs are looked up
- **THEN** they are requested in batches within the URL limit and each DOI is reported as matched or unmatched

### Requirement: Count estimate
The adapter SHALL provide result counts for the query preview through a single counting request per sub-query. The count SHALL be the de-duplicated union where the sub-queries overlap, or SHALL be labelled an upper bound when overlap is unknown.

#### Scenario: Preview count
- **WHEN** an editor requests test counts for a single-query OpenAlex strategy
- **THEN** the preview shows OpenAlex's reported count for that query
