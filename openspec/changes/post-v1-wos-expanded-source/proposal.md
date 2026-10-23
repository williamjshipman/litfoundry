# Proposal: Web of Science API Expanded source (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Design and tasks will be written when this change is scheduled.

## Why

WoS Starter returns only basic metadata, so v1 relies on DOI enrichment from OpenAlex and on WoS export files for full records. Institutions with WoS API Expanded entitlement can retrieve full records directly. These include abstracts, cited references, Keywords Plus and addresses (v1.3 §8).

## What Changes

- **Adapter:** a WoS API Expanded adapter against a versioned, configured endpoint. It uses the full tag set with `TS=` syntax and validates entitlement.
- **Records:** full-record normalisation, covering abstracts, cited references, Keywords Plus, author addresses, affiliations and countries.
- **Common rules:** budgets, typed errors, partial runs and licensed marking. The retired Lite API is never used.

## Capabilities

### New Capabilities

- `search/wos-expanded-source`: WoS API Expanded retrieval of full records, with entitlement validation and licensed marking.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.2: the WoS API Expanded adapter;
  - §2: the Data APIs row;
  - §7.2: WoS Expanded;
  - §8: Web of Science (Expanded).
- **Depends on:** `m3-search-runs`, `m3-source-credentials` and `m3-search-strategy` (WoS compiler, extended tag set).
- **Code:** `src/litfoundry/sources/wos_expanded.py`.
