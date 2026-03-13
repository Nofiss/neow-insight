# Frontend dashboard

Frontend React + TypeScript per Neow Insight, basato su Vite.

## Toolchain

- Package manager: `pnpm`
- Build/dev server: `vite`
- Styling: `tailwindcss` via plugin Vite (`@tailwindcss/vite`)
- Lint/format/check: `biome`

## Setup

```bash
pnpm install
```

## Comandi principali

```bash
pnpm run dev
pnpm run lint
pnpm run format
pnpm run check:fix
pnpm run build
pnpm run preview
```

## Note

- Il file di configurazione qualità codice è `frontend/biome.json`.
- Tailwind è integrato direttamente in Vite, quindi non è necessario PostCSS.
