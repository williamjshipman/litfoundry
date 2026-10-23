# Proposal: Scopus Search API source (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Design and tasks will be written when this change is scheduled.

## Why

In v1, users run the compiled Scopus query in Scopus's own interface and import the export file. Institutions with Elsevier API entitlements will want LitFoundry to run Scopus searches directly (v1.3 §8). pybliometrics holds its API keys and response cache process-wide, so the adapter must isolate each job's configuration.

## What Changes

- **Adapter:** a Scopus Search API adapter that executes the compiled `TITLE-ABS-KEY` query, with the effective credential, typed errors, retries, budgets and raw payload preservation.
- **Isolation:** each Scopus job runs either in its own subprocess, with its own configuration and a cache under the project's `temp/` directory, or through direct REST calls. Process-wide configuration is never shared between jobs.
- **Entitlement handling:** whether abstracts and references are available depends on the institution's entitlement. Coverage flags and partial runs reflect what was actually returned.
- **Licensed records:** Scopus API records are marked as licensed for export rights warnings.

## Capabilities

### New Capabilities

- `search/scopus-api-source`: Scopus Search API retrieval with per-job credential and cache isolation, entitlement-aware coverage and licensed marking.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.2: the Scopus Search API adapter;
  - §2: the Data APIs row;
  - §7.2: Scopus;
  - §8: Scopus.
- **Depends on:** `m3-search-runs`, `m3-source-credentials` and `m3-search-strategy` (Scopus compiler).
- **Code:** `src/litfoundry/sources/scopus.py`.
- **Dependencies:** pybliometrics, run in a subprocess, or direct REST calls. A licence review is needed.
