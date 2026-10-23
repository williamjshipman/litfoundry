# Spec Delta: analysis/citation-networks

## Purpose

Adds co-citation and bibliographic coupling analyses, which reveal a field's intellectual structure. Both are honest about how complete the underlying cited-reference data is.

## ADDED Requirements

### Requirement: Co-citation analysis
The system SHALL provide a co-citation network analysis (analysis 6). It SHALL link cited works or sources that are cited together by corpus works, with configurable similarity measure, normalisation, minimum co-citation threshold and graph size.

#### Scenario: Known co-citations
- **WHEN** analysis 6 runs on a fixture where two references are cited together by three works
- **THEN** the network links them with weight 3, before normalisation

### Requirement: Bibliographic coupling
The system SHALL provide a bibliographic coupling analysis (analysis 7). It SHALL link corpus works that share cited references, with configurable similarity measure, normalisation, threshold and graph size.

#### Scenario: Shared references
- **WHEN** two corpus works share four cited references
- **THEN** the coupling network links them with strength 4, before normalisation

### Requirement: Reference matching
References SHALL be matched across sources first by persistent identifiers, then by normalised reference strings. The analysis SHALL report the match method used and the match rate.

#### Scenario: Mixed sources
- **WHEN** a corpus combines OpenAlex works and a WoS export
- **THEN** references are matched by identifier where possible, and the report states how many were matched by string

### Requirement: Reference coverage
These analyses SHALL fail with an explanation when the corpus has no cited references. They SHALL warn with the coverage percentage when only some works have references.

#### Scenario: Starter-only corpus
- **WHEN** a corpus contains only WoS Starter records without enrichment references
- **THEN** analysis 6 fails and explains that cited references are missing
