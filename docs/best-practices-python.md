# Python Best Practices

This document captures Python best practices for this repository. It complements, but does not override, project instructions in `AGENTS.md`.

## Scope and Priority

When making implementation decisions, follow this order:

1. User request and task constraints.
2. Repository rules and architecture (`AGENTS.md`).
3. Existing code conventions in the touched module.
4. This document.

## Typing and Interfaces

- Add type hints to public and non-trivial functions.
- Prefer explicit return types for service and boundary functions.
- Use domain models/schemas for structured data instead of loose dictionaries.
- Keep function signatures small and clear; group related parameters into typed objects when appropriate.

## Project Layering

- Keep API route handlers thin.
- Put business/query logic in service modules.
- Keep ingestion/parsing logic in core ingestion modules.
- Keep DB concerns in DB/core layers and avoid leaking persistence details upward.

## Data and Error Boundaries

- Validate and normalize data at boundaries (API input, file input, external integrations).
- Raise specific exceptions with actionable messages.
- Catch broad exceptions only at orchestration boundaries (scripts, top-level loops), then log context.
- Preserve original error context when re-raising (`raise ... from exc`) where useful.

## Database and Transactions

- Make transactional boundaries explicit.
- Commit intentionally and rollback on failure.
- Keep query functions focused and predictable.
- Avoid hidden DB side effects in helper utilities.

## Paths, IO, and Configuration

- Prefer `pathlib.Path` for path operations.
- Keep filesystem and external IO operations explicit and isolated.
- Prefer file-based runtime configuration conventions used in this repo (`settings.toml`).

## Code Style and Maintainability

- Use clear names and small functions.
- Avoid deep nesting by returning early.
- Remove dead branches and unreachable code.
- Add comments only for non-obvious rationale, not obvious behavior.
- Keep imports grouped: standard library, third-party, local.

## Testing and Validation

- Add or update tests when behavior changes (API payloads, parsing, service logic).
- Prefer focused unit/service tests, plus API tests for contract changes.
- Useful commands:
  - `uv run ruff check .`
  - `uv run pytest`
  - `python scripts/verify.py` (full workflow)

## Review Checklist

- Types and interfaces are explicit.
- Layering is respected (router/service/core/db).
- Errors are specific and actionable.
- Transaction boundaries are clear.
- Tests and lint cover changed behavior.
