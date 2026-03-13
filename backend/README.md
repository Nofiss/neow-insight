# Backend Overview

This directory contains the FastAPI backend, ingestion pipeline, watcher integration, and SQLModel schema for Neow Insight.

## Requirements

- Python 3.12+
- `uv` installed

From repository root, sync backend dependencies with:

```bash
cd backend
uv sync
```

## Run Commands

From `backend/`:

```bash
# Start API in development mode
uv run api-dev

# Import all historical .run files once
uv run import-history

# Start watcher-only importer loop
uv run watch-history

# Lint
uv run ruff check .

# Test suite
uv run pytest
```

## Runtime Configuration

Runtime config is file-based (`settings.toml`) at repository root.

Expected settings sections:

- `[api]`: host, port, log_level
- `[storage]`: db_path, run_history_path
- `[watcher]`: enabled, debounce_seconds

Useful scripts from repository root:

```bash
python scripts/init_settings.py
python scripts/reset_settings.py
```

## Architecture

- `api/main.py`: app factory + lifespan startup/shutdown logic
- `api/routers/*`: route handlers
- `api/services/*`: business/query logic
- `core/ingestion/*`: parser and import/upsert pipeline
- `core/db/*`: SQLModel entities, engine, session helpers

Startup flow in `api/main.py`:

1. Initialize database schema.
2. Import history from configured `run_history_path`.
3. Apply import report to shared ingest status state.
4. Start filesystem watcher when enabled.

## Data Model

Primary tables (see `core/db/models.py`):

- `Run`: run metadata and outcome (`id`, `character`, `ascension`, `win`, `seed`)
- `CardChoice`: per-floor offered/picked card decision (`run_id`, `floor`, `picked_card`)
- `RelicHistory`: relic pickup timeline (`run_id`, `relic_id`, `floor`)

## Ingestion Pipeline

Main entrypoints:

- `import_history(history_path, session)`
- `import_run_file(run_file, session)`

Behavior:

- Parse `.run` JSON into normalized typed structures.
- Upsert run row by `run_id`.
- On update, rewrite dependent card/relic rows for that run.
- Commit on success; rollback on parse/runtime errors.

### Import Report and Diagnostics

Importer reports include counters:

- `scanned`
- `imported`
- `updated`
- `parse_errors`
- `skipped`

And recent structured issues (bounded list):

- `kind`: `parse_error` or `skipped`
- `file_path`: source `.run` file
- `message`: error detail
- `timestamp`: UTC ISO-8601 timestamp

This diagnostics payload is propagated to API ingest status.

## API Endpoints

- `GET /health`
  - Basic service status/version and watcher flag.

- `GET /runs/stats`
  - Global run totals and win rate.

- `GET /runs/card-insights?cards=...`
  - Per-card sample size/win-rate deltas for offered cards.

- `GET /recommendation?cards=...&character=...&ascension=...&floor=...`
  - Returns best pick with confidence, reason, scope, and fallback metadata.
  - Context params are optional.

- `GET /ingest/status`
  - Latest import counters + `recent_issues` diagnostics.
  - Includes latest processed pointers: `last_processed_run_id`, `last_processed_file`, `last_event_at`.

- `GET /live/context`
  - Returns latest observed card-choice context from DB (run id, character, ascension, floor, offered cards).

## Recommendation Semantics

Recommendation uses scoped fallback in this order:

1. `character_ascension_floor`
2. `character_ascension`
3. `character`/`ascension` (when partial context is provided)
4. `global`

Response includes:

- `scope`: selected scope used for scoring
- `applied_filters`: filters applied by selected scope
- `fallback_used`: whether a narrower requested context fell back
- `reason`: quality/availability reason (contextual/global variants)

## Testing Notes

Tests are in `backend/tests/`.

- API tests: `tests/test_api.py`
- Importer tests: `tests/test_importer.py`
- Parser tests: `tests/test_parser.py`

Run a focused subset:

```bash
uv run pytest tests/test_api.py tests/test_importer.py
```
