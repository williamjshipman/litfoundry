# Design: M5 review protocols and screening

## Context

Canonical works and merges exist (M4). Screening data lives in the project database, and reviewer IDs refer to `project_people` (v1.3 §4.2), because foreign keys cannot cross into the catalogue.

## Goals / Non-Goals

**Goals:**
- A decision ledger from which every PRISMA count and corpus membership can be recomputed.
- Blinding enforced by the server, not just hidden in the GUI.

**Non-Goals:**
- ASReview or AI prioritisation (post-v1). Nothing in this change implies automated recall.
- Full-text retrieval and reports (`m5-full-text-eligibility`).

## Decisions

### Ledger
- **`record_screening_decisions`:** append-only; the `version` increments per `(work_id, stage, reviewer_id)`.
- **`screening_resolutions`:** append-only; the latest resolution per `(work_id, stage)` wins.
- **`screening_state(work_id, stage, revision, final_decision, status)`:** a projection table updated in the same transaction as each event, used for queues, counts and optimistic concurrency. It can be rebuilt from the ledger by a maintenance command.

### Blinding
The decisions `GET` endpoint filters out other reviewers' decisions for works the caller has not yet decided at that stage, unless the caller is an adjudicator under the policy or the administrator. The filter is in the query layer and is tested at the API level.

### People
The first time an account acts in a project, a `project_people` row is upserted with its display name. Reviewer and actor IDs everywhere refer to it. This prepares for imported projects (`m7-project-export-import`).

### Merge resolution
The decision queries join through `works.merged_into_work_id` chains, to show and count decisions on retained works.

## Risks / Trade-offs

- [The projection drifts from the ledger] → It is updated transactionally, and a `reconcile`-style rebuild runs in tests comparing it with the ledger.
- [Large bulk jobs hold many works] → Bulk actions are batched into chunks of 500 works per job.

## Migration Plan

Project revision adding protocol, round, decision and resolution tables, and the `screening_state` projection.
