# Spec Delta: platform/web-security

## Purpose

Browser-facing security controls: a strict content security policy, protective headers, local-only assets, and rules that keep untrusted bibliographic content from executing in the GUI.

## ADDED Requirements

### Requirement: Strict content security policy
Every HTML response SHALL carry a `Content-Security-Policy` whose `script-src` is `'self'`, without `'unsafe-eval'` or `'unsafe-inline'`. The policy SHALL restrict all other resource types to the LitFoundry origin.

#### Scenario: CSP header present
- **WHEN** a browser loads the application page
- **THEN** the response's CSP contains `script-src 'self'` and neither `unsafe-eval` nor `unsafe-inline` for scripts

#### Scenario: No violations end to end
- **WHEN** the full end-to-end GUI suite runs
- **THEN** the browser reports zero CSP violations

### Requirement: No inline script
HTML served by LitFoundry SHALL contain no inline `<script>` content, inline event-handler attributes or import maps. All scripts SHALL be loaded with `<script src>` from the LitFoundry origin.

#### Scenario: Shell HTML inspected
- **WHEN** the served `index.html` is parsed
- **THEN** it contains no inline script, no `on*` attributes and no `importmap`

### Requirement: Locally served vendor assets
The GUI SHALL load Vue (runtime-only production build), Axios, ECharts and the compiled stylesheet only from local, exact-version copies served by LitFoundry, in development and in packages. A pinned fetch-and-verify script SHALL reject any vendor file whose checksum does not match the pinned value.

#### Scenario: Tampered vendor file
- **WHEN** a vendored file's content differs from its pinned checksum
- **THEN** the verify script exits with an error naming the file

#### Scenario: No external requests
- **WHEN** the GUI loads with all outbound internet blocked
- **THEN** every page renders and no request leaves the LitFoundry origin

### Requirement: Protective response headers
Responses SHALL include `X-Content-Type-Options: nosniff` and clickjacking protection (`frame-ancestors 'none'` and `X-Frame-Options: DENY`). Authenticated API responses SHALL be marked non-cacheable.

#### Scenario: Framing blocked
- **WHEN** another origin embeds LitFoundry in an iframe
- **THEN** the browser refuses to render it

### Requirement: Untrusted text rendered as text
Bibliographic metadata and other user- or source-supplied text SHALL be rendered as text nodes, never interpreted as HTML.

#### Scenario: Script in a title
- **WHEN** an imported record's title is `<img src=x onerror=alert(1)>`
- **THEN** the GUI shows the literal text and no script runs

### Requirement: No credentials in URLs
The API SHALL NOT accept passwords, tokens or API keys in URL query strings, and the GUI SHALL NOT place them there.

#### Scenario: Token in query string
- **WHEN** a client supplies an access token as a query parameter
- **THEN** the token is ignored and the request is treated as unauthenticated

### Requirement: Same-origin redirects only
Every redirect issued by LitFoundry, including post-sign-in return paths, SHALL target a relative path on the LitFoundry origin.

#### Scenario: Open redirect attempt
- **WHEN** sign-in is requested with a return path of `https://evil.example/`
- **THEN** the user is redirected to the home page instead

### Requirement: Origin check on unsafe methods
State-changing requests whose `Origin` (or, failing that, `Referer`) header names an origin other than the configured LitFoundry origin, or an origin on the explicit cross-origin allowlist, SHALL be rejected with 403 `FORBIDDEN`.

#### Scenario: Cross-site POST
- **WHEN** a POST arrives with `Origin: https://evil.example`
- **THEN** the response is 403 and nothing changes

#### Scenario: Allowlisted development origin
- **WHEN** a POST with a valid CSRF token arrives from an origin on the cross-origin allowlist
- **THEN** the origin check passes
