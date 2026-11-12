# Proposal: M1 web foundation

## Why

Every LitFoundry feature is delivered twice, through versioned REST endpoints and through the web GUI (v1.3 §0). Settling the API contract, browser security controls and SPA shell once avoids divergent error formats and CSP regressions. The GUI must run under a strict CSP (`script-src 'self'`, no `unsafe-eval`), which constrains how every later screen is built.

## What Changes

- Define the REST contract for every endpoint:
  - the `/api/v1` prefix;
  - JSON, UUID and UTC conventions;
  - the error envelope and standard codes, with `request_id`;
  - pagination and `If-Match` optimistic concurrency;
  - request size limits;
  - an OpenAPI document checked against the registered routes.
- Enforce browser security:
  - a strict CSP with no inline scripts or import maps;
  - clickjacking and MIME-sniffing headers;
  - same-origin redirects only;
  - no credentials in URLs;
  - untrusted bibliographic text rendered as text.
- Vendor Vue (runtime-only), Axios and ECharts as exact-version, checksum-verified local files. Build Tailwind CSS with the pinned standalone CLI.
- Add the SPA shell:
  - an in-house History-API router with server fallback;
  - an Axios client with credentials, CSRF header and typed errors;
  - shared loading, empty and error states;
  - confirmation dialogs;
  - an accessibility baseline.

## Capabilities

### New Capabilities

- `platform/api-conventions`: the common REST contract (prefix, formats, errors, pagination, concurrency, limits and OpenAPI).
- `platform/web-security`: CSP and security headers, vendored assets, safe rendering of untrusted text, redirect and URL-credential rules.
- `platform/web-shell`: SPA routing, the API client, shared UI states, destructive-action confirmation and the accessibility baseline.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §2: frontend build constraint;
  - §3: CSP and request limits;
  - §13: framework rules, accessibility, states and no `innerHTML`;
  - §14: conventions and standard errors;
  - §17: headers, origin checks and redirects;
  - §19: groups 14 and 13 (no-internet UI);
  - §20: M1 CSP acceptance.
- **Depends on:** `m1-platform-foundation`.
- **Code:** `src/litfoundry/api/` (error handling, pagination and ETag helpers), `frontend/` (`index.html`, `js/`, `css/`, `vendor/`), `scripts/` (vendor fetch/verify, Tailwind build), `docs/api.openapi.yaml`.
- **Out of scope:**
  - sign-in, CSRF token issuance and the `X-CSRF-TOKEN` check (`m1-local-identity`);
  - the 202 job pattern (`m2-background-jobs`).
