# Design: M5 full-text eligibility

## Context

The screening ledger exists (`m5-screening`), and the full-text stage reuses it. Write-once file storage and upload limits exist (M1 and M2).

## Goals / Non-Goals

**Goals:**
- Distinct work, report and study entities, which PRISMA counts can rely on.
- Safe file handling without native dependencies such as libmagic.

**Non-Goals:**
- PDF text extraction or annotation.
- Automatic retrieval through Unpaywall or publisher APIs. v1.3 forbids circumventing paywalls, and fetching is out of scope.

## Decisions

### Upload handling
- **Path:** the upload streams to the project's `temp/` directory, then the SHA-256 is computed.
- **Signature check:** `%PDF-` at offset 0 for PDF. The allowed types are configurable, each with its own signature check.
- **Scan:** the optional scanner command runs with the file path as an argument, with a timeout. A non-zero exit means rejected.
- **Storage:** write-once move to `attachments/<sha256[:2]>/<attachment_uuid>.pdf`.

### Downloads
- **Headers:** `Content-Disposition: attachment; filename*=UTF-8''<sanitised>`, `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`.
- **Access check:** the authorisation check runs on every request. There are no signed permanent URLs.

### Quotas
The per-project storage quota is configurable and enforced on upload, counting attachments, raw payloads and artifacts. The global defaults live in `m7-hardening`.

### Reports and studies
- **`full_text_reports`:** many per work.
- **`study_groups` and `study_work_links`:** a many-to-many link between works and studies.
- **Counting:** PRISMA counts come from these tables in `m5-corpus-and-prisma`.

## Risks / Trade-offs

- [PDFs can carry malicious content] → They are never rendered server-side and are always served as attachment downloads. Scanning is optional.
- [Deleting an attachment conflicts with the write-once rule] → Deletion is logical. File removal happens only in housekeeping, which never runs during a backup.

## Migration Plan

Project revision adding the reports, attempts, attachments and study tables.
