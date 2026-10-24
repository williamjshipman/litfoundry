# Design: M6 reports and interactive visualisations

## Context

Analysis runs and artifacts exist (`m6-bibliometric-analyses`). ECharts is vendored as a classic global build (`m1-web-foundation`).

## Goals / Non-Goals

**Goals:**
- Charts and graphs built from the same JSON the API returns, so the GUI views and exported data match.
- Reports that need nothing but a browser.

**Non-Goals:**
- PDF or Word report output (users can print to PDF).
- Report templating chosen by the user.

## Decisions

### Charts
- **Wrapper:** a thin render-function component around `echarts.init(el, null, {renderer: 'svg'})`.
- **CSP check:** the SVG renderer is used where CSP allows it. The end-to-end CSP collector verifies this, and the Canvas renderer is the fallback.
- **Networks:** force layout with server-side thresholding.
- **Export:** through `getDataURL` / `renderToSVGString`, posted to an artifact endpoint so that exports are recorded.

### Accessible tables
The table view reuses the paginated table component with sorting, fed from the same result JSON.

### Reports
- **Templating:** Jinja2 with `autoescape=True`.
- **Figures:** analysis figures are rendered on the server as static SVG with a small native SVG renderer, which avoids headless browsers. They are embedded inline as `<svg>` elements.
- **Script check:** the report contains no `<script>` element. A test parses the output and fails on any script, event handler or external URL.
- **Disclosure:** the PRISMA disclosure text is reused from `m5-corpus-and-prisma`.

### Report versioning
Each report is an artifact of kind `report`, with an incrementing version per project and corpus.

## Risks / Trade-offs

- [Server-side SVG figures differ visually from the interactive charts] → Accepted. Report figures are deliberately simple and static. The data comes from the same results.
- [Large inline SVG networks make reports heavy] → Report network figures respect the same size thresholds, with a note on any limit applied.
