# Proposal: Research maturity review table (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Design and tasks will be written when this change is scheduled.

## Why

Reviews in applied fields often classify studies by validation maturity, from theoretical work to sustained industrial use (v1.3 §12, analysis 10). Those categories are human judgements. They cannot be inferred from counts, so LitFoundry must record them as annotations with provenance and summarise them without implying automation.

## What Changes

- **Maturity labels:** reviewers can apply one human label per corpus work. The categories are theoretical, simulation, historic data, pilot, industrial advisory, closed-loop and sustained industrial use. Each label is recorded with reviewer, time and notes.
- **Analysis 10:** a research maturity review table summarising the labels by category and over time, with the unlabelled share reported.
- **Wording:** the table and reports describe the categories as human annotations, never as automatic conclusions.

## Capabilities

### New Capabilities

- `analysis/research-maturity`: human maturity annotations and the maturity review table.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.2: analysis 10;
  - §12: analysis 10.
- **Depends on:** `m6-bibliometric-analyses` and `m5-screening` (reviewer identities).
- **Code:** `src/litfoundry/bibliometrics/maturity.py`, a project migration revision for the annotations, and the GUI labelling controls.
