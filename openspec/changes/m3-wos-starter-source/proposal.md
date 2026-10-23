# Proposal: M3 Web of Science Starter source

## Why

The product owner put a Web of Science API adapter in v1 (v1.3 decision 7). The Clarivate WoS Starter API is the v1 route. It returns only basic metadata: no abstracts, cited references, Keywords Plus or addresses. It also has plan-dependent daily quotas. Starter records must therefore be enriched from OpenAlex by DOI, and gaps must be flagged so screening and analyses are honest about coverage (v1.3 §8).

## What Changes

- **API access:**
  - a WoS Starter adapter: `GET /apis/wos-starter/v1/documents`, `db=WOS`, with the `X-ApiKey` header;
  - page-number paging with at most 50 records per page;
  - the `q` parameter comes from the WoS compiler.
- **Quotas:** requests are recorded per key against daily budgets set from the plan quota. A run is `partial` when not all reported results can be paged.
- **Normalisation:** UT, DOI, ISSN, PMID, title, document type, source, authors, author keywords and times cited, with the retrieval date.
- **DOI enrichment:** Starter records are enriched from OpenAlex through batched lookups, with field-level OpenAlex provenance. The requester's OpenAlex credential and budget are used, and enrichment is skipped, with a warning, if no OpenAlex key is available.
- **Coverage flags:** records that still lack abstracts are flagged for screening. Missing references, affiliations and countries are reported as coverage gaps. The retired Lite API is never used.

## Capabilities

### New Capabilities

- `search/wos-starter-source`: WoS Starter retrieval, quota handling, normalisation, DOI enrichment from OpenAlex and coverage flags.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §2: the WoS Starter part of the Data APIs row;
  - §3: WoS Starter in the deployment topology;
  - §7.2: WoS Starter execution;
  - §8: Web of Science (Starter);
  - §19: group 6 (WoS Starter and DOI enrichment fixtures);
  - §20: M3.
- **Depends on:** `m3-search-runs`, `m3-source-credentials` and `m3-openalex-source` (DOI lookup).
- **Code:** `src/litfoundry/sources/wos_starter.py` and recorded fixtures.
- **Pre-release checks (v1.3 A.3):** confirm current Starter quotas, and the maximum number of records retrievable per query.
