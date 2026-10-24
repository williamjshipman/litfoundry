# Design: M1 web foundation

## Context

`m1-platform-foundation` provides the Flask app factory, Waitress serving and configuration. This change adds the cross-cutting HTTP contract and the browser shell that all later screens plug into. See proposal.md for scope.

## Goals / Non-Goals

**Goals:**
- One error and pagination contract, enforced by shared helpers rather than per-endpoint code.
- A frontend that runs under `script-src 'self'` with no build step other than Tailwind.

**Non-Goals:**
- Feature screens (each later change adds its own).
- Authentication (`m1-local-identity`).

## Decisions

### API contract
- **Errors:** all errors are raised as `ApiError(code, status, message, details)`. One Flask error handler renders the envelope, and unexpected exceptions map to `INTERNAL_ERROR` 500.
- **Request IDs:** a `before_request` hook assigns `request_id` (UUID4), and an `after_request` hook sets `X-Request-ID`.
- **Request and response models:** Marshmallow schemas. v1.3 §14 allows Marshmallow, Pydantic or equivalent; Marshmallow integrates with Flask and the apispec OpenAPI generator without replacing Flask or SQLAlchemy.
- **OpenAPI:** `docs/api.openapi.yaml` is hand-curated, and a contract test compares it with `app.url_map`. This avoids depending on a generator for completeness.
- **Pagination:** cursor pagination (`?limit=&cursor=`) with a default of 50 and a maximum of 500. Cursors are opaque, signed and encode the sort key and last ID, which gives stable results on large record tables (50,000+ works).
- **Concurrency:** ETag values are `W/"<revision>"`, and `If-Match` is required on PUT and PATCH for revisioned resources.
- **Error code additions:** `NOT_FOUND`, `PAYLOAD_TOO_LARGE`, `QUOTA_EXCEEDED` and `INTERNAL_ERROR` are added to the v1.3 §14 list, which says "include" and so is not exhaustive. They are recorded in `docs/decisions.md`.

### Frontend
- **Loading:** `frontend/index.html` loads, through `<script src>` in this order, `vendor/axios.min.js`, `vendor/echarts.min.js` and `js/main.js` (`type="module"`). `main.js` imports `../vendor/vue.runtime.esm-browser.prod.js` by relative path. There are no import maps and no inline scripts.
- **Components:** every component is an ES module whose `setup()` returns a render function built with `h()`. There are no `template` options and no `.vue` files.
- **Router:** an in-house module of about 150 lines, with a route table, path parameters, `history.pushState`/`popstate`, guards for authentication and admin routes, and link interception. vue-router is not used because its browser ESM build imports bare `'vue'`, which would need an import map (v1.3 A.2).
- **Vendoring:** `scripts/fetch_vendor.py` downloads pinned versions from the npm registry tarballs, checks SHA-256 values held in `scripts/vendor.lock.json`, and copies the licence files into `LICENSES/`. CI runs it in verify mode.
- **Tailwind:** `scripts/build_css.py` downloads the pinned standalone Tailwind binary per OS (checksum-verified) and builds `frontend/css/app.css` from `frontend/css/input.css`, scanning `frontend/js/**/*.js`. Class names in `h()` calls must be full literal strings.
- **Static serving:** Flask serves `frontend/` with long-cache headers for versioned vendor files. For non-`/api` GET requests that accept HTML, the SPA fallback returns `index.html`.

### Headers
- **Content Security Policy:**
  ```
  default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'
  ```
- **Inline styles:** `style-src` omits `'unsafe-inline'`. ECharts' SVG renderer sets inline style attributes through the DOM API, which CSP style-src does not block when the values are set through CSSOM. This is verified by the zero-violation end-to-end test; if it fails, the fallback is the Canvas renderer.

## Risks / Trade-offs

- [ECharts or Vue runtime emits a CSP violation in some browsers] → The end-to-end suite collects `securitypolicyviolation` events and fails on any of them; Chromium and Firefox are both run.
- [The hand-written router lacks features] → Keep the scope to what the screens need. Its unit tests cover parameters, guards and fallback.
- [Cursor pagination complicates "jump to page N"] → Totals are provided where cheap. The GUI uses next/previous navigation and filters rather than page numbers.

## Migration Plan

Not applicable.
