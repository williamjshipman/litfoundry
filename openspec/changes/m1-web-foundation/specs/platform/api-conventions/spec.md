# Spec Delta: platform/api-conventions

## Purpose

Defines the common contract every LitFoundry REST endpoint follows (versioned paths, data formats, errors, pagination, concurrency control and documentation), so clients can rely on uniform behaviour.

## ADDED Requirements

### Requirement: Versioned API prefix
Every REST route SHALL begin with `/api/v1`. Responses SHALL be JSON, except authorised binary downloads.

#### Scenario: Unknown API path
- **WHEN** a client requests a path under `/api/v1` that does not exist
- **THEN** the response is 404 with a JSON error body

### Requirement: Identifiers and timestamps
Resource identifiers in the API SHALL be UUIDs. Timestamps SHALL be server-generated UTC values in ISO-8601 format with a `Z` suffix.

#### Scenario: Timestamp format
- **WHEN** a client reads any resource with a creation time
- **THEN** the time is an ISO-8601 UTC string ending in `Z`

### Requirement: Error envelope
Every error response SHALL be JSON containing a stable machine-readable `code`, a human-readable `message`, optional field `details` and the request's `request_id`. Error responses SHALL NOT contain stack traces, SQL, file paths or secret material.

#### Scenario: Unhandled exception
- **WHEN** an endpoint raises an unexpected exception
- **THEN** the response is 500 with code `INTERNAL_ERROR` and a `request_id`
- **AND** the body contains no stack trace

### Requirement: Standard error codes
The API SHALL use a documented, fixed mapping of error codes to HTTP statuses, including:
- `VALIDATION_ERROR` 400
- `UNAUTHENTICATED` 401
- `FORBIDDEN` 403
- `NOT_FOUND` 404
- `CONFLICT` 409
- `RECORD_LOCKED` 409
- `PROJECT_BUSY` 409
- `QUOTA_EXCEEDED` 409
- `PAYLOAD_TOO_LARGE` 413
- `MAINTENANCE_IN_PROGRESS` 503

Every code in use SHALL appear in the OpenAPI document.

#### Scenario: Invalid body
- **WHEN** a client sends a body that fails schema validation
- **THEN** the response is 400 with code `VALIDATION_ERROR` and per-field details

### Requirement: Request identifiers
Every response SHALL carry a `request_id`, in an `X-Request-ID` header and in error bodies, that matches the server's log entries for that request.

#### Scenario: Request ID header
- **WHEN** any API request completes
- **THEN** the response has an `X-Request-ID` header

### Requirement: Server-side pagination
Collection endpoints SHALL be paginated on the server with a bounded maximum page size. Responses SHALL include the items, the page parameters and enough information to request the next page.

#### Scenario: Oversized page request
- **WHEN** a client requests more items per page than the maximum
- **THEN** the server returns at most the maximum page size

### Requirement: Optimistic concurrency
Editable resources SHALL expose their revision as an `ETag`. Updates SHALL require a matching `If-Match` header. A stale or missing revision SHALL be rejected with 409 `CONFLICT` and the current revision, without applying the change.

#### Scenario: Concurrent edit
- **WHEN** two clients read revision 3 and both submit updates with `If-Match` revision 3
- **THEN** the first update succeeds and the second returns 409 `CONFLICT`

### Requirement: Request size limits
The server SHALL enforce configurable maximum request body sizes, with separate limits for JSON bodies and file uploads. Larger requests SHALL be rejected with 413 `PAYLOAD_TOO_LARGE` before the body is processed.

#### Scenario: Oversized JSON
- **WHEN** a client posts a JSON body larger than the JSON limit
- **THEN** the response is 413 and nothing is persisted

### Requirement: OpenAPI document
The project SHALL publish `docs/api.openapi.yaml` describing every endpoint, request and response schema and error code. An automated test SHALL fail when a registered route is missing from the document, or a documented route is not registered.

#### Scenario: Undocumented route
- **WHEN** a developer adds a route without documenting it
- **THEN** the OpenAPI contract test fails
