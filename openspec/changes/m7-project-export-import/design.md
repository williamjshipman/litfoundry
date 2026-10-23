# Design: M7 project export and import

## Context

Every kind of project content now exists. Exports reuse the SQLite backup API and the write-once file guarantee. Imports reuse provisioning (staging, then atomic rename) and project migrations.

## Goals / Non-Goals

**Goals:**
- Exports that need no write barrier. A per-project consistent snapshot is enough.
- Imports that are safe against hostile archives.

**Non-Goals:**
- Merging an imported project into an existing one.
- Accepting archives from the unimplemented `brm` naming scheme (v1.3 §0.1).

## Decisions

### Export snapshot
- **No write scope:** the export job declares no write scope and takes no project write lease, so interactive edits and `append` jobs continue. (The `project` write scope would make every edit fail with `PROJECT_BUSY`, so it is not used.)
- **Export lease:** the job holds a named system lease, `export:<project_uuid>`, for its whole run. Housekeeping checks for this lease and skips every deletion of that project's files while it is held: attachment removal, artifact clean-up and export expiry.
- **Database snapshot:** taken through the SQLite backup API, which gives a consistent copy without blocking writers.
- **Inventory:** built from the snapshot's own file references (raw pages, imports, attachments, figures, reports, artifacts). Files are placed before the rows that reference them are committed (`m2-project-workspaces`), so every referenced file exists at snapshot time. Write-once files cannot change, and the lease stops housekeeping deleting them, so they are copied after the snapshot.
- **Packaging:** the ZIP is built with `zipfile` (ZIP64, deflate) in the project's `exports/` directory as `.partial`, verified with `testzip()`, then renamed.

### Export exclusions
Exports are assembled from an allowlist of project paths. They never copy the folder wholesale, so `temp/` and `exports/` are excluded by construction. The secret-leak scan runs in the tests.

### Licensed content
`source_runs.licensed` (from M3) determines whether licensed payloads exist. The metadata-only option omits `sources/` and `imports/` payloads for licensed runs, and records that in the manifest.

### Import validation
- **Order:** the central directory is read first. Every entry is checked for name safety (normalised, relative, no drive letters, no `..`), regular-file type (from external attributes), declared size and ratio.
- **Defaults:** a 2 GB limit on the expanded total, 50,000 entries and a 100:1 compression ratio, all configurable.
- **Extraction:** entries are streamed with size counting, and checksums are verified against `metadata/checksums.json`.

### Rekeying
- **What changes:** only `project_directory` gets a new UUID and folder. Inside `project.sqlite`, `project_info` and the manifest are rewritten with the new UUID. Work, study, corpus and decision IDs are unchanged, so corpus hashes survive.
- **People:** `project_people` rows with no matching account get `origin=imported`.
- **Provenance:** `imported_from_json` holds the original UUID, the export time and the source hostname from the manifest.

### Expiry housekeeping
A periodic job deletes expired exports. It skips runs while the `full-backup` lease is held.

## Risks / Trade-offs

- [Large exports take time and disk] → They run as jobs with progress, a free-space check first and per-user concurrency limits.
- [ZIP edge cases on different OSes] → Stdlib `zipfile` with explicit UTF-8 names, plus a Windows/Linux/macOS round-trip test in CI.

## Migration Plan

Catalogue revision adding `imported_from_json` to `project_directory`. Project revision adding an `exports` history table.
