# Spec Delta: platform/capacity-quotas

## Purpose

Protects a shared installation from resource exhaustion through configurable quotas with documented safe defaults, so no single user or project can starve the others.

## ADDED Requirements

### Requirement: Configurable quotas
The administrator SHALL be able to configure quotas for:
- projects per user;
- storage per project;
- maximum upload size;
- maximum archive size for export and import;
- queued jobs per user;
- concurrent jobs per user and the number of workers, which are limits enforced by queuing.

Every quota SHALL have a documented safe default.

#### Scenario: Defaults documented
- **WHEN** an administrator reads the configuration reference
- **THEN** every quota is listed with its default and meaning

### Requirement: Quota enforcement
An action that would exceed a quota SHALL be refused before any work is done, with 409 `QUOTA_EXCEEDED` naming the quota, its limit and current usage. There are two exceptions:
- size limits on a request body use `PAYLOAD_TOO_LARGE`;
- concurrency limits never refuse. A job above the concurrent-jobs or worker limit stays queued, as background jobs specify.

#### Scenario: Project limit
- **WHEN** a user at their project quota creates another project
- **THEN** the response is 409 `QUOTA_EXCEEDED` naming the project quota

#### Scenario: Concurrency limit queues
- **WHEN** a user already running the maximum number of concurrent jobs submits another
- **THEN** the new job is accepted and stays `queued` until capacity frees

#### Scenario: Queue limit refuses
- **WHEN** a user already has the maximum number of queued jobs and submits another
- **THEN** the response is 409 `QUOTA_EXCEEDED` naming the queued-jobs quota

### Requirement: Administrator exemption
The administrator SHALL be able to exceed per-user project quotas when acting as administrator. Storage quotas SHALL still apply to every project.

#### Scenario: Admin creates project
- **WHEN** the administrator creates a project beyond the per-user limit
- **THEN** the project is created

### Requirement: Usage visibility
The administrator SHALL see per-user and per-project usage against quotas. Users SHALL see their own usage and the usage of the projects they can read.

#### Scenario: Storage usage
- **WHEN** an owner opens a project's settings
- **THEN** its storage usage and quota are shown
