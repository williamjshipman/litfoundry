# Spec Delta: records/deduplication

## Purpose

Finds and resolves duplicate works across and within sources accurately and reversibly. Raw records, review history and frozen corpora are never damaged, and PRISMA duplicate counts stay correct.

## ADDED Requirements

### Requirement: Staged duplicate detection
Duplicate detection SHALL run these stages in order:
1. normalised DOI equality;
2. equality of other persistent identifiers (OpenAlex ID, UT, PMID, EID);
3. normalised exact title with matching year and overlapping authors;
4. fuzzy candidate matching.

Each candidate SHALL record the stage that found it.

#### Scenario: DOI duplicate
- **WHEN** an OpenAlex work and a Scopus import share a DOI
- **THEN** they are identified as duplicates at the DOI stage

### Requirement: Blocked fuzzy matching
Fuzzy matching SHALL compare only works that share a blocking key (for example, publication year ±1 and a normalised title prefix or n-gram), never all pairs. It SHALL complete for 50,000 works within the configured job time budget.

#### Scenario: Large corpus
- **WHEN** deduplication runs on the 50,000-work fixture
- **THEN** it finishes within the job budget, and the number of pairs compared is far below all pairs

### Requirement: Candidate scoring
Each candidate pair SHALL have a score and the factors behind it: title similarity, year difference, author overlap, venue match and identifier agreement or conflict.

#### Scenario: Factors shown
- **WHEN** a user inspects a fuzzy candidate
- **THEN** the score and each contributing factor are shown

### Requirement: Automatic merges for exact identifiers
When the project setting is on (the default), pairs found by the DOI or persistent-identifier stages SHALL be merged automatically. Each automatic merge SHALL be recorded as a reversible merge decision by the system, with its reason. All other candidates SHALL await manual review.

#### Scenario: Automatic DOI merge
- **WHEN** deduplication finds a DOI match with automatic merging on
- **THEN** the pair is merged and a system merge decision is recorded

#### Scenario: Setting off
- **WHEN** automatic merging is turned off
- **THEN** DOI matches are queued as pending candidates instead

### Requirement: Possible versions are not auto-merged
Pairs that look like different versions of a work SHALL be flagged as possible versions and SHALL never be merged automatically. Examples are a conference paper and a journal article with similar titles but different DOIs or document types.

#### Scenario: Conference and journal versions
- **WHEN** a conference paper and a later journal article have near-identical titles and different DOIs
- **THEN** they appear as a flagged candidate for manual review and are not merged

### Requirement: Candidate queue
`GET /api/v1/projects/{project_id}/duplicates` SHALL return candidates, paginated and filterable by status (`pending`, `merged`, `rejected` or `deferred`), stage and score, to users with read access.

#### Scenario: Pending queue
- **WHEN** a reviewer requests pending candidates sorted by score
- **THEN** the highest-scoring pending pairs are returned first

### Requirement: Duplicate decisions
`POST /api/v1/projects/{project_id}/duplicates/decisions` SHALL let editors merge (naming the retained work), reject, defer or undo a decision. Each decision SHALL record the actor, time, reason and affected works. Merges and undos SHALL run as `records`-scope jobs over the affected works.

#### Scenario: Manual merge
- **WHEN** an editor merges a candidate pair, keeping work A
- **THEN** work B points to work A and the decision records the editor and reason

#### Scenario: Reject
- **WHEN** an editor rejects a candidate
- **THEN** the pair is marked `rejected` and is not proposed again unless the works change

### Requirement: Merges preserve history
A merge SHALL NOT delete works, raw records or screening decisions. The merged work SHALL keep its ID and point to the retained work. The retained work SHALL take the merged work's source memberships, and earlier review decisions SHALL stay attached to their original work IDs and visible on the retained work.

#### Scenario: Corpus survives merge
- **WHEN** a work in a frozen corpus is later merged into another work
- **THEN** the corpus still resolves the original work ID through its merge pointer

### Requirement: Reversible merges
Undoing a merge SHALL restore both works, their source memberships and their canonical values to their state before the merge. It SHALL record an audit event.

#### Scenario: Undo
- **WHEN** an editor undoes a merge
- **THEN** both works are separate again with their original memberships

### Requirement: Overlap and duplicate accounting
Source memberships after merging SHALL determine:
- the source-overlap counts (works found by one, several or all sources);
- the PRISMA count of duplicate records removed.

#### Scenario: Overlap count
- **WHEN** 100 OpenAlex works and 80 WoS works share 30 merged works
- **THEN** overlap shows 30 works found in both and PRISMA records 30 duplicates removed

### Requirement: Deduplication screen
The Dedup screen SHALL show candidate pairs side by side, with confidence reasons and accept, reject, defer and undo actions. It SHALL offer bulk safe actions limited to candidates above a chosen score with identical identifiers, and these SHALL require confirmation.

#### Scenario: Bulk safe action
- **WHEN** an editor bulk-accepts identical-DOI candidates above a threshold and confirms
- **THEN** those candidates are merged in one `records`-scope job
