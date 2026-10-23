# Design: M3 OpenAlex source

## Context

The adapter plugs into the `m3-search-runs` runner and the `m3-source-credentials` budget guard. See proposal.md.

## Goals / Non-Goals

**Goals:**
- A small, stateless adapter with no module-global configuration.
- Union counting that is exact for the records actually retrieved.

**Non-Goals:**
- OpenAlex snapshot or bulk downloads.
- Endpoints other than `/works`.

## Decisions

### No PyAlex
- **Why:** PyAlex sets its API key and email in module-level `pyalex.config`, which would leak across concurrent jobs in one worker (v1.3 §8, A.3).
- **Instead:** `httpx` directly, with a per-job client.

### Requests
- **Endpoint:** `GET https://api.openalex.org/works`.
- **Parameters:**
  - `search.title_abstract_keywords=...` or `search.title_and_abstract=...`;
  - `filter=publication_year:2015-2026,type:article|review,language:en`;
  - `per-page=200`;
  - `cursor=*`;
  - `select=` to limit fields.
- **Field selection:** `select` is used to reduce payload, keeping every field that normalisation needs.

### Union counting
- **Runs:** each sub-query is retrieved fully, and every retrieved OpenAlex ID is stored per sub-query.
- **Reported count:** the number of distinct IDs once all sub-queries complete.
- **Incomplete sub-queries:** if any sub-query is `partial`, the source run is `partial`. The provisional reported count is then the provider's maximum sub-query count plus the distinct IDs retrieved from the others, labelled as an estimate.

### Normalisation
- **Abstract:** `abstract_inverted_index` is reconstructed by sorting positions.
- **Identifiers:** `doi` is normalised to lowercase without the URL prefix.
- **Authors:** `authorships` provide authors, institutions and country codes.
- **Keywords:** `keywords` and `topics` map to keywords, with their scheme recorded.
- **References:** `referenced_works` provide the cited OpenAlex IDs.
- **Citations:** `cited_by_count` is stored with its retrieval timestamp.

### DOI batches
`filter=doi:<a>|<b>|...` with up to 50 DOIs per request (URL-length bound), using `select` to limit fields.

### Fixtures
Recorded responses in `tests/fixtures/openalex/` cover:
- success;
- multi-page cursor;
- 401, 403 and 429;
- missing abstract;
- cost headers;
- DOI batches with misses.

CI never calls the live API.

## Risks / Trade-offs

- [OpenAlex changes parameter names or pricing] → Isolated in one module with fixtures. There is a pre-release check (v1.3 A.3).
- [Large unions use memory] → Store IDs in a temporary SQLite table in the project `temp/` directory, not in Python sets.
