# Spec Delta: search/search-runs

## Purpose

Executes a project's search against the enabled bibliographic APIs as reproducible, auditable runs. Each run records exactly what was requested, reported and retrieved, and never loses one source's results because another source failed.

## ADDED Requirements

### Requirement: Launch a search
`POST /api/v1/projects/{project_id}/search-runs` SHALL be available to editors, owners and the administrator. It SHALL:
- capture an immutable strategy version;
- compile the strategy for every enabled API source;
- create one source run per enabled API source;
- start a background job;
- respond 202 with the job and search run IDs.

#### Scenario: Launch with two sources
- **WHEN** an editor launches a search with OpenAlex and WoS Starter enabled
- **THEN** one search run with two source runs is created and a job is queued

#### Scenario: Viewer cannot launch
- **WHEN** a viewer launches a search
- **THEN** the response is 403

### Requirement: Disabled sources make no calls
A source that is disabled for the project SHALL generate zero outbound API calls in previews, counts, searches and enrichment.

#### Scenario: Disabled provider
- **WHEN** a search runs with WoS disabled
- **THEN** no request is sent to any WoS endpoint

### Requirement: Source run record
Each source run SHALL record:
- provider, origin, query version, credential scope and requester;
- the executed request, without credentials;
- `reported_count`, `retrieved_count` and `completeness` (`complete` or `partial`);
- status and `error_code`;
- `missing_required_fields_count`;
- a checksum over the retrieved payloads;
- start and end times.

#### Scenario: Completed run
- **WHEN** a source run retrieves all reported records
- **THEN** it records equal reported and retrieved counts and completeness `complete`

### Requirement: Counts are not proof of retrieval
Completeness SHALL be `partial` whenever:
- fewer records were retrieved than reported;
- retrieval stopped early because of an error, the budget or a limit;
- the provider cannot page through all results.

#### Scenario: Provider paging limit
- **WHEN** a provider reports 12,000 results but allows retrieving only 10,000
- **THEN** the source run is `partial` with retrieved count 10,000 and an explanation

### Requirement: Raw payload preservation
Every provider response page SHALL be stored unchanged, append-only, as a write-once file under the project's `sources/<search_run_uuid>/<source>/raw/` directory, with:
- its SHA-256;
- the response schema or version;
- the original query;
- the pagination state.

#### Scenario: Payload kept
- **WHEN** a source run completes
- **THEN** every retrieved page exists on disk with a recorded SHA-256 that matches its content

### Requirement: Normalised source records
Each retrieved record SHALL also be stored as an adapter-normalised record linked to its raw record. Records that lack required fields (abstract, references or identifiers) SHALL be counted in `missing_required_fields_count`.

#### Scenario: Missing abstracts counted
- **WHEN** 40 of 100 retrieved records lack an abstract
- **THEN** `missing_required_fields_count` reflects them and the records are flagged

### Requirement: Typed source errors
Adapters SHALL map provider failures to typed codes: `AUTH_REQUIRED`, `ACCESS_DENIED`, `INVALID_QUERY`, `RATE_LIMITED`, `SOURCE_UNAVAILABLE`, `PARTIAL_RESULTS` and `UNSUPPORTED_FILTER`. The API SHALL report them as `SOURCE_ACCESS_DENIED`, `SOURCE_RATE_LIMITED`, `SOURCE_PARTIAL` or the closest standard error.

#### Scenario: Revoked key
- **WHEN** the provider rejects the key during a run
- **THEN** the source run fails with `ACCESS_DENIED` and the API reports `SOURCE_ACCESS_DENIED`

### Requirement: Bounded retries
Adapters SHALL retry only retryable failures (rate limiting and temporary unavailability), with exponential backoff that honours `Retry-After`, up to a bounded number of attempts.

#### Scenario: Rate limited then recovered
- **WHEN** a provider returns 429 with `Retry-After: 2` once and then succeeds
- **THEN** the adapter waits at least 2 seconds, retries and the run continues

### Requirement: Independent sources
A failed source run SHALL NOT discard or roll back another source run's results. A search run with mixed outcomes SHALL show each source's status.

#### Scenario: One source fails
- **WHEN** OpenAlex succeeds and WoS Starter fails in the same search run
- **THEN** the OpenAlex records are kept and the search run is `partial`

### Requirement: Resumable retrieval
Pagination state SHALL be saved at each checkpoint. A search job reclaimed after a crash SHALL resume from the last saved state, without duplicating stored records.

#### Scenario: Worker crash mid-run
- **WHEN** a worker dies after page 5 of 10 and the job is reclaimed
- **THEN** retrieval resumes at page 6 and pages 1–5 are not stored twice

### Requirement: Outbound request restrictions
Outbound requests SHALL go only to provider endpoints hardcoded or allowlisted in provider configuration, with TLS verification and timeouts. No user-supplied URL SHALL ever be fetched.

#### Scenario: URL injection
- **WHEN** a query override contains a full URL to another host
- **THEN** no request is sent to that host

### Requirement: Per-request credentials
Credentials SHALL be passed with each request by the job that owns them. They SHALL never be placed in process-wide library configuration. Concurrent jobs SHALL each use only their own requester's credentials.

#### Scenario: Concurrent users
- **WHEN** two users with different personal keys run searches at the same time in one worker
- **THEN** each provider request carries the key of the job that issued it

### Requirement: Search history
`GET /api/v1/projects/{project_id}/search-runs` SHALL list search runs, and `GET /api/v1/projects/{project_id}/search-runs/{run_id}` SHALL return a run's status, per-source counts, completeness, errors and query versions, to users with read access. The Search history/results tab SHALL present them.

#### Scenario: History view
- **WHEN** a viewer opens Search history
- **THEN** each run lists its sources with reported and retrieved counts and completeness
