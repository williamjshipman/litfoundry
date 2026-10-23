# Spec Delta: platform/web-shell

## Purpose

The single-page application shell every LitFoundry screen runs in: client routing, the API client, shared UI states, destructive-action confirmation and the accessibility baseline.

## ADDED Requirements

### Requirement: Client routing with server fallback
The GUI SHALL use History-API routes with clean paths. The server SHALL return the application shell for any non-API GUI path, so deep links and browser reloads work.

#### Scenario: Deep link reload
- **WHEN** a user reloads the browser on a nested GUI path
- **THEN** the shell loads and the router shows the matching screen

#### Scenario: Unknown GUI path
- **WHEN** the router has no screen for a path
- **THEN** a not-found screen with a link home is shown

### Requirement: API client behaviour
The GUI's API client SHALL call only the same-origin `/api/v1`, send cookies, attach the CSRF token header to unsafe methods, and turn error responses into typed errors that carry `code`, `message` and `request_id`.

#### Scenario: Error shown with reference
- **WHEN** an API call fails with a server error
- **THEN** the user sees a readable message and the `request_id` to quote to the administrator

### Requirement: Session expiry handling
When an API call returns 401, the GUI SHALL attempt one session refresh and repeat the call. If refresh fails, it SHALL show the sign-in page and return to the original route after sign-in.

#### Scenario: Expired access token
- **WHEN** the access token has expired but the refresh token is valid
- **THEN** the user's action completes without a visible sign-in

### Requirement: Shared data states
Every screen that loads data SHALL show distinct loading, empty, error-with-retry and loaded states.

#### Scenario: Failed load retried
- **WHEN** a list fails to load and the user selects Retry
- **THEN** the request is repeated and the loaded list replaces the error state

### Requirement: Destructive action confirmation
Destructive actions SHALL require explicit confirmation in a dialog that names what will be affected. Destructive actions are deleting, revoking, merging, overwriting and disabling.

#### Scenario: Cancelled deletion
- **WHEN** a user starts a deletion and cancels the confirmation
- **THEN** no request is sent

### Requirement: Accessibility baseline
Every screen SHALL be operable by keyboard alone, give every control an accessible name, show a visible focus indicator and use a responsive layout that works from tablet to desktop widths.

#### Scenario: Keyboard-only navigation
- **WHEN** a user navigates the sign-in page and the home page using only the keyboard
- **THEN** every control can be reached and activated, with visible focus
