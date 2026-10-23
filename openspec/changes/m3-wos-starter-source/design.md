# Design: M3 Web of Science Starter source

## Context

The adapter plugs into the search runner. It uses the OpenAlex adapter's batched DOI lookup for enrichment. See proposal.md.

## Goals / Non-Goals

**Goals:**
- Use only the Starter API, within its quotas.
- Enrichment provenance that is visible at field level.

**Non-Goals:**
- WoS API Expanded (`post-v1-wos-expanded-source`).
- Times-cited data on Free Trial plans, which lack it.

## Decisions

### Requests
- **Endpoint:** `GET https://api.clarivate.com/apis/wos-starter/v1/documents?db=WOS&q=<compiled>&limit=50&page=<n>`, with header `X-ApiKey`.
- **Paging stops when:** a page returns fewer than `limit` records, the metadata total is reached, or the provider's maximum retrievable page is reached. The last case makes the run `partial`.
- **Quota rejections:** 429 responses, or provider quota messages, map to `RATE_LIMITED` when transient. When the response indicates a daily quota is exhausted, they map to a budget stop.

### Enrichment
- **When it runs:** a second phase of the same job, after retrieval, and only when OpenAlex is reachable and a credential exists.
- **Lookup:** DOIs are collected and passed to `openalex.lookup_dois(batch)`.
- **Storage:** the matched OpenAlex works are stored as raw and normalised records of an enrichment source run (`provider=openalex`, `origin=api`, linked to the WoS source run). M4's canonicalisation therefore attributes the enriched fields to OpenAlex naturally.
- **Effect on WoS completeness:** none. Enrichment has its own completeness.

### Fixtures
Recorded Starter responses in `tests/fixtures/wos_starter/` cover:
- multi-page results;
- an invalid key;
- quota exhaustion;
- records without DOIs;
- the paging limit.

## Risks / Trade-offs

- [The maximum retrievable records per query is undocumented (v1.3 A.3)] → It is configurable with a conservative default, and the run is marked `partial` beyond it. Verify before release.
- [Quota response format is unknown] → Map conservatively: unrecognised 4xx quota responses become `SOURCE_RATE_LIMITED` with the provider message kept in the run record.
