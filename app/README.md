# Web app (`app/`)

Frontend for the Global Fire Harmonization project (working name: *Many Witnesses*). Owner: Member 3. Task: T-030 (setup and skeleton).

**Status:** application shell only. It shows a placeholder page and no data. The map, calendar, charts and evidence panels are added by later tasks (T-031 onward). The app will talk only to the API or the static JSON export, never to Parquet files directly (`docs/ARCHITECTURE.md`).

## Prerequisites

- Node.js 22.12+ or 24 LTS (`docs/TECH_STACK.md` §7). Node 20 is end-of-life and too old for Vitest 5.
- npm (installed with Node).

## Commands

Run all commands from this `app/` directory.

| Command | What it does |
|---|---|
| `npm ci` | Install the exact versions from `package-lock.json` |
| `npm run dev` | Start the dev server (Vite prints the local URL) |
| `npm run build` | Type-check (strict TypeScript), then build to `dist/` |
| `npm run typecheck` | Type-check only |
| `npm test` | Run the Vitest tests once |
| `npm run lint` | Run the template's default linter (Oxlint) |
| `npm run preview` | Serve the built `dist/` locally |

## Stack (approved, D-008)

React 19, Vite 8, TypeScript (strict), MapLibre GL JS 6, deck.gl 9, terra-draw, Apache ECharts 6, TanStack Query, Vitest. The map, drawing and chart libraries are installed but not used yet. Exact versions are pinned in `package-lock.json`.

## Folder map

```
app/
├── index.html          page entry
├── src/
│   ├── main.tsx        app root; mounts the TanStack Query provider
│   ├── App.tsx         placeholder shell
│   ├── index.css       base styles and visible focus
│   └── *.test.ts(x)    Vitest tests
├── public/             static files
└── package.json        scripts and dependencies
```

Folders for the API client, state, components and content are added when the task that needs them starts.

## Rules for this folder

- Components consume only the documented data contract (`docs/DATA_CONTRACT.md`).
- No science in the app: no conversions, baselines, probabilities or verdicts.
- Never commit `node_modules/`, `dist/`, secrets or data products.
