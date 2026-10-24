# Tasks: M6 reports and interactive visualisations

## 1. Visualisations

- [ ] 1.1 Build the ECharts render-function wrapper (SVG renderer, Canvas fallback) and the chart components for trends and rankings. Verify with Playwright, with zero CSP violations (§19 group 14).
- [ ] 1.2 Build the network graph component (zoom, pan, hover, select, weight and degree filters, size disclosure). Verify with a Playwright test on a fixture network.
- [ ] 1.3 Build accessible table alternatives for every chart. Verify with a keyboard-only Playwright test.
- [ ] 1.4 Implement view export (SVG, PNG, CSV, JSON) recorded as artifacts. Verify with a Playwright download test.
- [ ] 1.5 Build the Bibliometrics tab (corpus selector, schema-driven parameter form, dashboard, artifacts). Verify with an end-to-end test that runs an analysis from the GUI (§19 group 12, analysis).

## 2. Reports

- [ ] 2.1 Implement the report job, templates (methods, sources, PRISMA, analyses, limitations, provenance, partial-source disclosure, and the citation source/date labels and quality caveat) and the server-side static SVG figures. Verify with a fixture report test asserting each section and the caveat.
- [ ] 2.2 Implement the safety checks (autoescape, no scripts, no external references). Verify with a parser-based test and a hostile-title fixture.
- [ ] 2.3 Implement `POST /api/v1/projects/{project_id}/reports` and versioning. Verify with API tests.
- [ ] 2.4 Build the Reports tab. Verify with a Playwright test.
- [ ] 2.5 Document the report contents and limitations wording. Verify that the docs show an example report.
