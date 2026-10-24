# Spec Delta: analysis/interactive-visualisations

## Purpose

Lets users explore bibliometric results through interactive, accessible charts and network graphs that work offline under the strict content security policy, and export what they see.

## ADDED Requirements

### Requirement: Interactive charts
Results with counts, trends or rankings SHALL be displayed as interactive charts, with hover details and series filtering.

#### Scenario: Trend chart
- **WHEN** a user opens an annual-trends result
- **THEN** a chart shows the counts per year with hover details

### Requirement: Interactive network graphs
Network results SHALL be displayed as interactive graphs that support zoom, pan, hover, node selection and filtering by weight or degree. Selecting a node SHALL show its details and connected nodes.

#### Scenario: Select node
- **WHEN** a user selects an author node in a coauthorship graph
- **THEN** the node's details and its coauthors are highlighted

### Requirement: Graph size disclosure
Network views SHALL show the node and edge counts before and after thresholding, and the thresholds applied.

#### Scenario: Thresholded network
- **WHEN** a network is limited to its top 100 nodes
- **THEN** the view states the original and displayed node and edge counts

### Requirement: Accessible alternatives
Every chart and graph SHALL have an accessible, sortable table alternative containing the same data.

#### Scenario: Table view
- **WHEN** a keyboard user switches a chart to table view
- **THEN** the same data is shown in a sortable table

### Requirement: Export from views
Users SHALL be able to export the current chart or graph view as SVG or PNG, and its data as CSV or JSON. Each export SHALL be recorded as an artifact with provenance.

#### Scenario: Export SVG
- **WHEN** a user exports a network view as SVG
- **THEN** an SVG artifact linked to the analysis run is created and downloaded

### Requirement: CSP-compliant rendering
Charts and graphs SHALL render using only locally served scripts, without triggering any content security policy violation.

#### Scenario: Chart under CSP
- **WHEN** the end-to-end suite renders every chart type
- **THEN** zero CSP violations are reported

### Requirement: Bibliometrics tab
The Bibliometrics tab SHALL provide:
- a corpus selector;
- a parameter form generated from each analysis type's parameter declaration;
- a dashboard of results, with graph and table views;
- downloads of the run's artifacts.

#### Scenario: Run from the tab
- **WHEN** an editor selects a corpus and analysis type, sets parameters and runs it
- **THEN** progress is shown and the results open in the dashboard when complete
