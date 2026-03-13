# AGENTS.md

Guidance for coding agents operating in this repository.

## Repository Overview

- Monorepo with Python backend and React/TypeScript frontend.
- Main directories:
  - `backend/`: FastAPI API, ingestion, watcher, SQLModel models.
  - `frontend/`: Vite React dashboard, TanStack Query, Tailwind/shadcn-style components.
  - `scripts/`: root automation scripts (`dev`, `e2e`, `verify`, settings scripts).
  - `data/`: local SQLite database (gitignored).

## Rule Files Check

Scanned for agent-specific rule files:

- `.cursorrules`: not found
- `.cursor/rules/`: not found
- `.github/copilot-instructions.md`: not found

If any of these files are added later, follow them as higher-priority project instructions.

## Build, Lint, Test Commands

Run commands from the repository root unless otherwise noted.

### Full workflow (recommended before handoff)

- `python scripts/verify.py`
  - Runs backend lint + backend tests + frontend lint + frontend build.

### Development startup

- `python scripts/dev.py`
  - Starts backend and frontend together for local development.

### End-to-end smoke

- `python scripts/e2e.py`
  - Starts temporary backend on port `8010` and validates key API responses.

## Backend Commands (`backend/`)

- Install/sync environment:
  - `uv sync`
- Run API in dev mode:
  - `uv run api-dev`
- Import historical runs:
  - `uv run import-history`
- Start watcher importer:
  - `uv run watch-history`
- Lint:
  - `uv run ruff check .`
- All tests:
  - `uv run pytest`

### Run a single backend test (important)

- Single file:
  - `uv run pytest tests/test_api.py`
- Single test function:
  - `uv run pytest tests/test_api.py::test_health_endpoint`
- Pattern filter:
  - `uv run pytest -k recommendation`
- Stop on first failure:
  - `uv run pytest -x`

## Frontend Commands (`frontend/`)

- Install dependencies:
  - `npm install`
- Start dev server:
  - `npm run dev`
- Lint:
  - `npm run lint`
- Build:
  - `npm run build`
- Preview build:
  - `npm run preview`

Note: no frontend test runner is configured currently; lint + build are the quality gates.

## Settings and Runtime Configuration

- Runtime config is file-based (`settings.toml`), not shell env vars.
- Initialize config from template:
  - `python scripts/init_settings.py`
- Reset from template:
  - `python scripts/reset_settings.py`

Expected sections in `settings.toml`:

- `[api]`: `host`, `port`, `log_level`
- `[storage]`: `db_path`, `run_history_path`
- `[watcher]`: `enabled`, `debounce_seconds`

## Architecture and Layering

Backend design:

- Keep route handlers thin (`backend/api/routers/*`).
- Keep business/query logic in services (`backend/api/services/*`).
- Keep parsing/ingestion in core (`backend/core/ingestion/*`).
- Keep DB schema/session under `backend/core/db/*`.
- App lifecycle in `backend/api/main.py` via lifespan context.

Frontend design:

- Keep feature code under `frontend/src/features/recommendation/*`.
- Keep API calls in `api.ts`.
- Keep query hooks in `hooks.ts`.
- Keep dashboard composition in `recommendation-dashboard.tsx`.
- Reuse UI primitives from `frontend/src/components/ui/*`.

## Code Style Guidelines

## Python

- Target Python 3.12+.
- Use `from __future__ import annotations` in new Python modules.
- Use absolute imports from project packages (`api.*`, `core.*`).
- Add type annotations for function signatures and non-trivial returns.
- Prefer `pathlib.Path` over raw string paths.
- Naming:
  - `snake_case` for functions/variables/modules
  - `PascalCase` for classes/dataclasses
  - `UPPER_SNAKE_CASE` for constants

### Python imports

- Order imports as:
  1) standard library
  2) third-party
  3) local modules
- Separate groups with a blank line.
- Avoid wildcard imports.

### Python error handling

- Raise specific exceptions at parse/validation boundaries (e.g. run parse failures).
- At DB boundaries, use commit/rollback explicitly.
- Catch broad exceptions only in boundary orchestration code (scripts/import loops).
- Preserve clear, actionable error messages.

## TypeScript/React

- Respect `strict` TypeScript config; avoid `any`.
- Keep API types centralized in feature `types.ts`.
- Use typed API wrappers and hooks (`api.ts`, `hooks.ts`).
- Use functional components and hooks only.
- Naming:
  - `PascalCase` for components
  - `camelCase` for variables/functions
  - hooks must start with `use`

### TypeScript imports

- Prefer `@/` alias imports for app code.
- Group imports as external first, internal second.
- Avoid deep relative paths when alias is available.

### UI and async behavior

- Reuse existing shadcn-style primitives before adding new base components.
- Preserve loading/error/empty states for async panels.
- Keep query keys stable and descriptive.
- Use `enabled` in React Query for conditional requests.

## Testing Guidance

- Follow existing backend test patterns in `backend/tests/`:
  - API tests with FastAPI `TestClient`
  - in-memory SQLite via `StaticPool`
  - dependency overrides for DB session
- Update or add tests when changing:
  - endpoint payload shapes
  - ingestion/parser behavior
  - settings scripts semantics

## Handoff Checklist for Agents

- Run relevant checks for your scope.
- Prefer full validation before final handoff:
  - `python scripts/verify.py`
- Ensure no local artifacts are committed (`__pycache__`, `*.pyc`, local DB files).
- Keep commits focused and message intent clearly (`feat:`, `fix:`, `chore:`, `docs:`).
