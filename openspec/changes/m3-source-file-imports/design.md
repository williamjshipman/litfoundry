# Design: M3 source file imports

## Context

Source runs, raw records and normalised source records exist (`m3-search-runs`). File imports reuse them with `origin=file_import`.

## Goals / Non-Goals

**Goals:**
- One importer per format, with a shared validation pipeline.
- The same normalised record shape as API adapters, so M4 does not care where a record came from.

**Non-Goals:**
- PDF parsing.
- Importing EndNote XML or reference-manager libraries beyond BibTeX and RIS.

## Decisions

### Upload handling
- **Streaming:** the upload streams to the project's `temp/` directory under the upload size limit.
- **Hashing:** the file's SHA-256 is computed while streaming.
- **Storage:** once validation passes, the file moves write-once to `imports/<source_run_uuid>/<original-name-sanitised>`.

### Format detection
Format is detected by signature first, then the declared format is confirmed. A mismatch is a validation error.

| Format | Signature |
|---|---|
| WoS plain text | `FN `/`VR ` headers |
| RIS | `TY  -` |
| BibTeX | `@type{` |
| Scopus CSV | header columns |
| WoS tab-delimited | header columns |
| OpenAlex JSON | top-level `results` array or a work object |

### Parsers
- **BibTeX:** `bibtexparser` v2.
- **RIS:** `rispy`.
- **CSV and tab-delimited:** the standard-library `csv` module.
- **WoS plain text:** a small tag-based parser, because no maintained library exists.
- **OpenAlex JSON:** reuses the OpenAlex adapter's `normalize()`.

### Encoding
Encoding is detected through a BOM, then UTF-8 with an explicit fallback to `cp1252` for legacy WoS and Scopus exports. The detected encoding is recorded.

### Job
The import job is an `append`-scope job. Records are inserted in batches inside `write_unit()`, with checkpoints between batches.

## Risks / Trade-offs

- [Provider export formats drift] → Fixtures come from real anonymised exports, one per format, and parser versions are recorded in the source run.
- [Large CSVs] → Streaming parse and batched inserts, with a configurable record cap.

## Migration Plan

Project revision adding `licensed` and `import_filename` columns to `source_runs`.
