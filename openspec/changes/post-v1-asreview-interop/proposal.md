# Proposal: ASReview interoperability (post-v1)

**Priority:** SHOULD, planned for the release after v1 (v1.3 §0.2). Design and tasks will be written when this change is scheduled.

## Why

Some teams prioritise title/abstract screening with ASReview. LitFoundry should exchange screening data with ASReview without embedding an ASReview server. Labels from ASReview must still go through human adjudication, and LitFoundry must not imply that AI prioritisation guarantees complete recall (v1.3 §2, §11).

## What Changes

- **Export:** `GET /projects/{project_id}/screening/asreview` exports a de-duplicated screening input CSV with work IDs.
- **Import:** `POST /projects/{project_id}/screening/asreview` imports labelled results matched by work ID, with reviewer provenance. Imported labels are recorded as attributed decisions that require human adjudication before they become final.
- **Recall disclosure:** the GUI and reports state that prioritised screening does not guarantee complete recall.

## Capabilities

### New Capabilities

- `review/asreview-interop`: ASReview CSV export, labelled-result import with provenance, mandatory human adjudication and recall disclosure.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §0.2: ASReview;
  - §2: the Screening row;
  - §11: ASReview;
  - §14: `/screening/asreview`.
- **Depends on:** `m5-screening`.
- **Code:** `src/litfoundry/review/asreview.py`.
