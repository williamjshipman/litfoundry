# Tasks: M1 web foundation

## 1. API contract

- [x] 1.1 Implement `ApiError`, the error handler, `INTERNAL_ERROR` mapping and the `X-Request-ID` hooks. Verify with API tests that an unexpected exception returns 500 with `request_id` and no stack trace.
- [x] 1.2 Define the error-code registry with fixed HTTP statuses and expose it to the OpenAPI document. Verify with a unit test that every registered code maps to a single status.
- [x] 1.3 Implement cursor pagination helpers (default and maximum limits, signed cursors). Verify with unit tests for maximum clamping and tampered-cursor rejection.
- [x] 1.4 Implement ETag/`If-Match` helpers that return 409 `CONFLICT` with the current revision. Verify with a concurrent-update test.
- [x] 1.5 Enforce JSON and upload size limits that return 413 `PAYLOAD_TOO_LARGE`. Verify with API tests.
- [x] 1.6 Create `docs/api.openapi.yaml` and the route/document contract test. Verify that the test fails for a seeded undocumented route.
- [x] 1.7 Implement UUID and UTC ISO-8601 (`Z`) serialisation helpers and a JSON 404 for unknown `/api/v1` paths. Verify with API tests.

## 2. Browser security

- [x] 2.1 Add the CSP and protective headers to every response (HTML and API) and the non-cacheable header on authenticated API responses. Verify with header tests.
- [x] 2.2 Implement the `Origin`/`Referer` check on unsafe methods, accepting the configured origin and the cross-origin allowlist. Verify that a cross-site POST returns 403 and an allowlisted origin passes (§19 group 14).
- [x] 2.3 Implement a safe-redirect helper that accepts relative return paths only. Verify with an open-redirect test.
- [x] 2.4 Ensure tokens in query strings are ignored. Verify with an API test.

## 3. Vendored frontend assets

- [x] 3.1 Add `scripts/fetch_vendor.py` and `scripts/vendor.lock.json` for the Vue runtime ESM production build, `axios.min.js` and `echarts.min.js`, with licences copied to `LICENSES/`. Verify that tampering with a file makes the verify mode fail.
- [x] 3.2 Add `scripts/build_css.py` with the pinned standalone Tailwind CLI and checksum. Verify that `frontend/css/app.css` builds on Windows, Linux and macOS CI.

## 4. SPA shell

- [x] 4.1 Create `frontend/index.html` (no inline script) and `js/main.js` mounting a render-function root component. Verify with a test that parses `index.html` for inline scripts, `on*` attributes and import maps.
- [x] 4.2 Implement the in-house History-API router (params, guards, not-found) and the server SPA fallback. Verify with router unit tests (run under pytest via a small JS test harness or Playwright) and a deep-link reload end-to-end test.
- [x] 4.3 Implement the Axios client (same origin, credentials, CSRF header hook, typed errors, one refresh retry on 401). Verify with Playwright tests against stubbed endpoints.
- [x] 4.4 Implement shared components for the loading, empty and error-with-retry states and the confirmation dialog. Verify with Playwright component checks.
- [x] 4.5 Implement text-only rendering helpers and a lint rule that forbids `innerHTML` in `frontend/js`. Verify with an XSS end-to-end test using a hostile title fixture (§19 group 14).
- [x] 4.6 Add the Playwright CSP-violation collector, used by every end-to-end test, and an offline test that blocks all non-origin requests. Verify with zero violations on the shell and sign-in pages (§20 M1 acceptance, §19 groups 13–14).
- [x] 4.7 Add a keyboard-only and accessible-name check for the shell (axe-core run from Playwright, vendored for tests only). Verify that it passes on the sign-in and home pages.
