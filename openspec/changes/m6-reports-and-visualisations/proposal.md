# Proposal: M6 reports and interactive visualisations

## Why

Researchers explore results interactively and publish them as figures and reports. The reports must state methods, sources, limitations and provenance (v1.3 §12). All of this must run under the strict CSP, with no remote assets.

## What Changes

- **Interactive charts and network graphs:** rendered with vendored ECharts, with zoom, filter, hover and select. Each chart has an accessible table alternative and shows graph size and thresholds. Views export to SVG and PNG, and their data to CSV and JSON.
- **Bibliometrics tab:**
  - a corpus selector;
  - a parameter form generated from the analysis parameter schemas;
  - a dashboard and graph view;
  - sortable tables;
  - artifact downloads.
- **Reports (`/reports`):** versioned, self-contained HTML reports containing:
  - methods;
  - sources and search strings, with dates and counts;
  - the PRISMA diagram and disclosure;
  - selected analyses;
  - limitations and methodological notes;
  - provenance.

  Reports contain no scripts, escape all metadata and are stored as artifacts.
- **GUI:** the Reports tab.

## Capabilities

### New Capabilities

- `analysis/interactive-visualisations`: interactive charts and networks, accessible alternatives, view export, and the Bibliometrics tab.
- `analysis/research-reports`: versioned, self-contained HTML reports with methods, sources, limitations and provenance.

### Modified Capabilities

None.

## Impact

- **v1.3 sections implemented:**
  - §2: Visualization (ECharts);
  - §12: outputs and the HTML report;
  - §13: the Bibliometrics and Reports tabs;
  - §14: `/reports`;
  - §19: groups 12 (analysis in end-to-end tests) and 14 (CSP across charts);
  - §20: M6.
- **Depends on:** `m6-bibliometric-analyses` and `m5-corpus-and-prisma`.
- **Code:** `frontend/js/` (chart and graph components), `src/litfoundry/bibliometrics/reports/` (HTML templating with autoescape) and the API routes.
- **Dependencies introduced:** Jinja2 (BSD), which Flask already includes, used for report templates with autoescaping.
