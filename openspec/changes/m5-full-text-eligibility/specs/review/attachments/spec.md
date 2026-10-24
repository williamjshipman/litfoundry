# Spec Delta: review/attachments

## Purpose

Stores full-text files uploaded by authorised users safely and serves them only to people with access, protecting the server and other users from malicious or oversized files.

## ADDED Requirements

### Requirement: Upload attachments
`POST /api/v1/projects/{project_id}/attachments` SHALL accept full-text uploads from editors, owners and the administrator. Each file SHALL be stored write-once under the project's `attachments/` directory with a generated name, recording:
- SHA-256 and size;
- detected MIME type;
- original filename, as metadata only;
- uploader and time.

#### Scenario: Upload PDF
- **WHEN** an editor uploads a PDF
- **THEN** it is stored with a generated name and its metadata is recorded

### Requirement: Content validation
Uploads SHALL be accepted only when the file signature matches an allowed type, PDF by default. A declared MIME type or extension that does not match SHALL be rejected. Files over the size limit, or that would exceed the project's storage quota, SHALL be rejected.

#### Scenario: Disguised executable
- **WHEN** a user uploads an executable renamed to `.pdf`
- **THEN** the upload is rejected and nothing is stored

#### Scenario: Quota exceeded
- **WHEN** an upload would exceed the project's storage quota
- **THEN** it is rejected with `QUOTA_EXCEEDED`

### Requirement: Duplicate files reused
Uploading a file whose SHA-256 matches an existing attachment in the project SHALL link to the existing attachment instead of storing a second copy.

#### Scenario: Same file twice
- **WHEN** the same PDF is uploaded for two reports
- **THEN** both reports reference one stored attachment

### Requirement: Authorised download
`GET /api/v1/projects/{project_id}/attachments/{attachment_id}` SHALL serve the file only to users with read access, checked at request time, as a download with a safe filename and `nosniff`. `GET /api/v1/projects/{project_id}/attachments` SHALL list attachments.

#### Scenario: No access
- **WHEN** a user without read access requests an attachment by ID
- **THEN** the response is 404 and no content is served

### Requirement: Delete attachments
`DELETE /api/v1/projects/{project_id}/attachments/{attachment_id}` SHALL let editors remove an attachment from use and record an audit event. Housekeeping SHALL remove the stored file once no report references it.

#### Scenario: Delete
- **WHEN** an editor deletes an attachment no report uses
- **THEN** it disappears from listings and housekeeping later removes the file

### Requirement: Optional scanning
When the administrator configures a scan command, every upload SHALL be scanned before acceptance. Files the scanner rejects SHALL be refused, and a scanner failure SHALL reject the upload.

#### Scenario: Scanner rejects
- **WHEN** the configured scanner flags an upload
- **THEN** the upload is refused and nothing is stored

### Requirement: Files tab
The Files tab SHALL list the project's attachments and stored files, with size, type, uploader and linked reports, and offer authorised download.

#### Scenario: List files
- **WHEN** a viewer opens the Files tab
- **THEN** attachments are listed and can be downloaded
