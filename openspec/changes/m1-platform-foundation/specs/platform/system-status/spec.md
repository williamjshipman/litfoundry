# Spec Delta: platform/system-status

## Purpose

Lets operators and the administrator see whether LitFoundry is alive and healthy, without exposing internal details to anyone else.

## ADDED Requirements

### Requirement: Liveness endpoint
`GET /api/v1/health/live` SHALL respond without authentication, with a minimal status body that contains no version numbers, paths, hostnames or configuration.

#### Scenario: Anonymous liveness
- **WHEN** an unauthenticated client calls `GET /api/v1/health/live` on a running server
- **THEN** the response is 200 with a minimal status body

### Requirement: Readiness endpoint
`GET /api/v1/health/ready` SHALL be available only to the administrator and SHALL report:
- catalogue reachability;
- schema version status;
- application and Python versions;
- free disk space for the data root;
- configured run mode, hostname and trusted proxies.

#### Scenario: Admin readiness
- **WHEN** the administrator calls `GET /api/v1/health/ready`
- **THEN** the response lists each check with its status

#### Scenario: Non-admin refused
- **WHEN** a non-admin user or an anonymous client calls `GET /api/v1/health/ready`
- **THEN** the response is 401 or 403 and contains no diagnostic detail

### Requirement: Host status command
`litfoundry status` SHALL print on the host the same health checks and versions as the readiness endpoint, without requiring a web session.

#### Scenario: Status on host
- **WHEN** an operator runs `litfoundry status` against a data root
- **THEN** it prints health, application version and schema versions, and exits non-zero if any check fails

### Requirement: Admin system screen
The administrator console SHALL show a system screen with versions, run mode, hostname and proxy configuration and the readiness checks. It SHALL never show secret values.

#### Scenario: System screen
- **WHEN** the administrator opens Admin → System
- **THEN** versions, run mode, hostname, proxy configuration and check results are shown
