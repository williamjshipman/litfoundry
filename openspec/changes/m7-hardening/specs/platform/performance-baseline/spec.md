# Spec Delta: platform/performance-baseline

## Purpose

Sets measurable baseline performance targets and a load-test gate, so LitFoundry stays responsive for several concurrent users on large projects. The targets are baselines, not guarantees.

## ADDED Requirements

### Requirement: Large-project pagination
Every list of records, candidates, decisions or artifacts SHALL use server-side pagination and filtering. It SHALL stay responsive for projects with 50,000 or more works.

#### Scenario: 50,000 works
- **WHEN** a user pages through records in a project with 50,000 works
- **THEN** each page loads without transferring the full record set to the browser

### Requirement: Dashboard response time
A typical project dashboard (Overview) SHALL return within 2 seconds on a modern LAN server for a project with 10,000 source records, measured at the server.

#### Scenario: Overview timing
- **WHEN** the load-test fixture project's Overview is requested
- **THEN** the server responds within 2 seconds at the 95th percentile

### Requirement: Non-blocking requests
No web request SHALL wait for a bibliographic API call or other long-running work. Such work SHALL run in jobs.

#### Scenario: Slow provider
- **WHEN** a provider takes 30 seconds to respond during a search
- **THEN** other web requests are unaffected

### Requirement: Load-test gate
Before release, a load test SHALL run with several simultaneous viewers and editors on a project of at least 10,000 source records, with a search job and an analysis job running. It SHALL pass the response-time targets, with no errors other than expected conflicts.

#### Scenario: Release gate
- **WHEN** the load test runs against a release candidate
- **THEN** it meets the targets and reports no unexpected errors

### Requirement: Restart resilience
After a process crash or machine reboot:
- leases SHALL expire and jobs SHALL be recovered;
- no job SHALL be reported as completed without its committed results;
- no catalogue entry SHALL be left without its project, or the reverse, after reconciliation;
- project files and results SHALL persist.

#### Scenario: Power loss
- **WHEN** the server host is hard-stopped during a search and an analysis and then restarted
- **THEN** both jobs are recovered or failed cleanly, and all committed data is present
