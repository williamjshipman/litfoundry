# Spec Delta: platform/server-deployment

## Purpose

Defines LitFoundry's two run modes, LAN server mode behind a TLS reverse proxy and single-machine workstation mode, and the network boundaries each enforces.

## ADDED Requirements

### Requirement: Loopback-only application listener
`litfoundry serve` SHALL bind the production WSGI server to `127.0.0.1` on a configurable port (default `5080`). It SHALL refuse to start if configured to listen for plaintext HTTP on a non-loopback interface.

#### Scenario: Default bind
- **WHEN** `litfoundry serve` starts with default configuration
- **THEN** it listens on `127.0.0.1:5080` only

#### Scenario: Non-loopback bind refused
- **WHEN** the configured bind address is `0.0.0.0`
- **THEN** `litfoundry serve` exits with an error and does not listen

### Requirement: Explicit run mode
The installation SHALL be configured explicitly for either `server` mode or `workstation` mode. LitFoundry SHALL NOT infer the mode at runtime.

#### Scenario: Mode missing
- **WHEN** `litfoundry serve` starts without a configured run mode
- **THEN** it exits with an error that names the setting to choose

### Requirement: Server mode over HTTPS
In server mode, LAN clients SHALL reach LitFoundry only through HTTPS, terminated by a TLS reverse proxy on a stable internal hostname. The project SHALL ship a reference Caddy configuration that uses the placeholder hostname `litfoundry.example.internal`, redirects HTTP to HTTPS and proxies to the loopback listener.

#### Scenario: HTTP redirected
- **WHEN** a LAN browser requests `http://` on the configured hostname
- **THEN** the reverse proxy redirects to `https://`

#### Scenario: Hostname is configuration
- **WHEN** the operator configures a different hostname
- **THEN** LitFoundry works under that hostname without code changes

### Requirement: Trusted proxies
LitFoundry SHALL honour forwarded-for, forwarded-proto and forwarded-host headers only from configured trusted proxy addresses. Otherwise it SHALL use the connecting peer's address and scheme.

#### Scenario: Spoofed forwarded header
- **WHEN** a request whose peer is not a trusted proxy carries `X-Forwarded-For: 10.9.9.9`
- **THEN** the client address recorded for throttling and logging is the peer address

### Requirement: Host allowlist
LitFoundry SHALL reject requests whose `Host` header is not in the configured allowlist, with status 400 and no application processing.

#### Scenario: Unknown host
- **WHEN** a request arrives with `Host: evil.example`
- **THEN** the response is 400

### Requirement: Workstation mode
In workstation mode, LitFoundry SHALL serve the browser on the same host at `http://localhost:<port>`, without a reverse proxy and without LAN access. All authentication, authorisation and CSRF rules SHALL still apply.

#### Scenario: Workstation access
- **WHEN** workstation mode is configured and the browser opens `http://localhost:5080`
- **THEN** the sign-in page is served
- **AND** another computer cannot connect

### Requirement: Same-origin by default
The GUI and the API SHALL be served from one origin, and cross-origin requests SHALL be refused by default. Cross-origin access SHALL be enabled only for explicitly allowlisted origins, with credentials and never with a wildcard origin.

#### Scenario: Unlisted origin
- **WHEN** a request from an origin that is not allowlisted performs a CORS preflight
- **THEN** no `Access-Control-Allow-Origin` header is returned

### Requirement: No development server in production
Server and workstation modes SHALL run only under the production WSGI server, with debug mode off. Any configuration that enables the framework's debug server SHALL be refused outside the development command.

#### Scenario: Debug refused
- **WHEN** debug mode is enabled in configuration for `litfoundry serve`
- **THEN** the command exits with an error

### Requirement: Offline operation
LitFoundry SHALL keep serving existing projects without internet access. Online source searches SHALL fail with a clear, retryable error. The GUI SHALL load no code, styles or fonts from any origin other than the LitFoundry origin.

#### Scenario: No internet
- **WHEN** the host has no internet access
- **THEN** users can sign in, open projects and view results
- **AND** a source search fails with a source-unavailable error that can be retried later

### Requirement: Deployment documentation
The documentation SHALL describe:
- HTTPS reverse-proxy setup;
- distributing organisational or Caddy internal CA trust to Windows, macOS, Linux and browsers;
- restricting the inbound firewall rule to trusted subnets;
- the fact that clients do not automatically trust Caddy's internal CA.

#### Scenario: Documentation present
- **WHEN** the release documentation is built
- **THEN** it contains the proxy, CA trust and firewall sections for each supported operating system
