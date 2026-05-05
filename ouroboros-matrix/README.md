# CORTEX Persist Product Dashboard

React/Vite prototype for the canonical product demo behind issue `#209`.

## What it shows

- Persistent sidebar + topbar product shell
- KPI strip, verification trend, decision table, audit timeline, and proof package route
- Narrative flow: `store -> verify -> tamper -> audit -> export proof`
- Hash routes:
  - `#/`
  - `#/decisions/:decisionId`
  - `#/proofs/:decisionId`

## Run

```bash
npm install
npm run dev
```

## Data sources

You can also install `eslint-plugin-react-x` and `eslint-plugin-react-dom` for
React-specific lint rules.

Without query params, the app uses embedded mock data.

To load external JSON, pass `data` in the query string:

```text
http://localhost:5173/?data=/dashboard-data.json#/
```

Supported JSON shapes:

- Native dashboard bundle with `generatedAt`, `kpiMetrics`, `trendSeries`, `decisionRecords`
- CLI-style proof artifact with `audit_receipt` + `cryptographic_proof`
- Lineage artifact with `cortex_lineage_proof` + `facts`

Bundled examples:

- `/dashboard-data.json`
- `/audit-proof-artifact.json`
- `/audit-pack-evidence-demo.json`

If external loading fails or the payload shape is unsupported, the UI falls back to embedded mock data and shows that state in the footer.
