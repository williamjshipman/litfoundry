# Spec Delta: search/api-budgets

## Purpose

Tracks the cost of every bibliographic API call per key and enforces daily budgets, so metered keys (OpenAlex usage, WoS Starter quotas) cannot be exhausted by one user or one runaway search.

## ADDED Requirements

### Requirement: Usage recording
Every outbound bibliographic API call SHALL be recorded against the credential used, with:
- provider;
- job;
- requester;
- timestamp;
- cost, taken from the provider's reported cost where one is available (OpenAlex's credits-used header) and otherwise from the request count.

#### Scenario: OpenAlex cost recorded
- **WHEN** an OpenAlex response reports its cost in the credits-used header
- **THEN** that cost is added to the key's usage for the current UTC day

### Requirement: Daily budget per key
Each credential SHALL have a configurable daily budget, which resets at midnight UTC. When a call would exceed the budget, the job SHALL stop calling that provider, keep the results already retrieved, mark the source run `partial` and record `SOURCE_BUDGET_EXCEEDED`.

#### Scenario: Budget exhausted mid-search
- **WHEN** a key's daily budget runs out during a search
- **THEN** the search keeps the records retrieved so far and the source run shows `partial` with `SOURCE_BUDGET_EXCEEDED`

### Requirement: Per-user cap on shared keys
The administrator SHALL be able to set a per-user daily cap on use of each shared key. A user who reaches the cap SHALL be stopped with `SOURCE_BUDGET_EXCEEDED`, while other users can still use the key.

#### Scenario: One user capped
- **WHEN** one user reaches their cap on the shared OpenAlex key
- **THEN** their further calls are refused and another user's search with the same key proceeds

### Requirement: Warning before an expensive search
When a search's estimated calls exceed the remaining budget of the effective key or cap, the system SHALL warn the user before the search starts, and SHALL require explicit confirmation to proceed.

#### Scenario: Estimate above remaining budget
- **WHEN** a user launches a search estimated at 500 calls with 100 calls left on the key
- **THEN** the launch requires confirmation and states that the run will be partial

### Requirement: Usage views
The administrator SHALL see usage and remaining budget for every shared and personal key. Each user SHALL see usage and remaining budget for their own personal keys, and their remaining cap on shared keys.

#### Scenario: Admin usage view
- **WHEN** the administrator opens Admin → API keys
- **THEN** each key shows today's usage, its budget and its status
