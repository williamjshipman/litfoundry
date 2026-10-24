# Tasks: M6 bibliometric analyses

## 1. Framework

- [ ] 1.1 Add the project revision for `analysis_runs` and `artifacts`. Verify with migration tests.
- [ ] 1.2 Implement the analysis registry, parameter schemas and `POST`/`GET /api/v1/projects/{project_id}/analyses` and `GET .../analyses/{analysis_id}`, as read-only jobs. Verify with API tests, including unsupported types and invalid parameters.
- [ ] 1.3 Implement frozen-snapshot reads (no live `works` access), the input hash (snapshot hash, parameters, dictionary rule content, engine version), seeded randomness and provenance recording. Verify with a re-run reproducibility test, and a test that editing a member work after freezing changes neither the results nor the input hash (§19 group 9).
- [ ] 1.4 Implement `BibliometricsEngine`, `BibliumEngine` (with a startup smoke test) and `NativeEngine`. Verify with parity tests on fixtures and a test that the fallback is used when the capability check fails.

## 2. v1 analyses

- [ ] 2.1 Implement annual trends (analysis 1). Verify with deterministic count fixtures (§19 group 9).
- [ ] 2.2 Implement productivity rankings with coverage warnings (analysis 2). Verify with fixtures that have missing affiliations.
- [ ] 2.3 Implement per-source citation rankings with labels (analysis 3). Verify with a test that counts are never summed.
- [ ] 2.4 Implement coauthorship networks with thresholds and size limits (analysis 4). Verify with a small known network fixture (§19 group 9).
- [ ] 2.5 Implement keyword frequency and co-occurrence using the dictionary revision (analysis 5). Verify with fixtures.
- [ ] 2.6 Implement source overlap and completeness (analysis 9). Verify with a known overlap fixture.
- [ ] 2.7 Implement the prerequisite-field checks (fail or warn with coverage), including a reference-coverage flag. Verify with tests (§19 group 9).

## 3. Artifacts

- [ ] 3.1 Implement artifact writing and recording, `GET /api/v1/projects/{project_id}/artifacts` and authorised, checksum-verified `GET .../artifacts/{artifact_id}`. Verify with API tests, including tampered-file and no-access cases.
- [ ] 3.2 Implement CSV and JSON table exports with formula neutralisation. Verify with a formula-injection test.
- [ ] 3.3 Document each analysis's method, parameters and limitations in `docs/`. Verify that every registered type is documented.
