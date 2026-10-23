# Proposal: M3 OpenAlex source

## Why

OpenAlex is the open bibliographic source that every installation can use, and the only v1 API source with abstracts and cited-work IDs. It is also used to enrich WoS Starter records by DOI. OpenAlex now needs an API key for cursor paging and meters usage in dollars (v1.3 §8, A.3). The adapter must therefore treat the key as required, send it in a header, record each call's cost and respect per-key budgets.

## What Changes

- A direct HTTPS REST adapter for the OpenAlex works endpoint. It does not use PyAlex, whose key setting is module-global.
- **Key handling:** the key is required and sent as `Authorization: Bearer`.
- **Retrieval:**
  - cursor paging;
  - published-date, document-type and language filters;
  - rate-limit compliance.
- **Cost:** each response's cost is read from `X-RateLimit-Credits-Used` and fed into budgets.
- **Split queries:** each sub-query runs, the union is de-duplicated by OpenAlex ID, and the reported count is the size of the de-duplicated union.
- **Normalisation:**
  - abstract reconstruction;
  - authors, institutions and countries;
  - keywords and topics;
  - referenced work IDs;
  - citation count with its retrieval date;
  - records that lack abstracts or references are flagged.
- **DOI lookup:** batched DOI lookups, used for WoS Starter enrichment.
- **Count estimates** for the query preview.

## Capabilities

### New Capabilities

- `search/openalex-source`: OpenAlex retrieval, authentication, cost recording, split-query union counting, normalisation and batched DOI lookup.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §2: the OpenAlex part of the Data APIs row;
  - §7.2: OpenAlex de-duplicated union counts;
  - §8: OpenAlex;
  - §19: groups 5 (union counts) and 6 (OpenAlex fixtures);
  - §20: M3.
- **Depends on:** `m3-search-runs` and `m3-source-credentials`.
- **Code:** `src/litfoundry/sources/openalex.py` and recorded-response fixtures. No live paid credentials are used in CI.
- **Pre-release check (v1.3 A.3):** confirm current OpenAlex pricing, the cost header and key requirements.
