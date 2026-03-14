# React Best Practices

This document captures React and TypeScript best practices for this repository. It complements, but does not override, project instructions in `AGENTS.md`.

## Scope and Priority

When deciding implementation details, follow this order:

1. User request and task constraints.
2. Repository rules and architecture (`AGENTS.md`).
3. Existing code conventions in the same feature area.
4. This document.

## TypeScript and API Contracts

- Keep `strict` typing intact; avoid `any`.
- Prefer explicit domain types over inline ad hoc object literals.
- Centralize feature API types in the feature `types.ts`.
- Model nullable/optional states explicitly instead of broad unions with weak narrowing.
- Narrow unknown input close to boundaries (API adapters, parsing utilities).

## Component Design

- Keep components focused on one clear responsibility.
- Extract repeated UI or logic only when it reduces complexity.
- Prefer composition over deeply configurable monolith components.
- Keep props small and intentional; pass callbacks with precise signatures.
- Derive display state from data when possible, instead of duplicating local state.

## State and Data Fetching

- Keep server state in query hooks; avoid mirroring query data into local state.
- Use stable, descriptive query keys.
- Use `enabled` for conditional queries.
- Handle loading, error, and empty states explicitly in async panels.
- Keep network access in API modules and expose typed hook wrappers.

## Effects and Hooks

- Prefer computed values in render over `useEffect` where possible.
- Use effects only for side effects (subscriptions, imperative integrations, syncing external systems).
- Keep dependency arrays complete and stable; avoid disabling lint rules unless justified.
- Build custom hooks for reusable logic with clear input/output contracts.

## Rendering and Performance

- Optimize only where measurable or likely on hot paths.
- Use memoization (`useMemo`, `useCallback`) for expensive or identity-sensitive values, not by default.
- Keep list rendering keyed with stable IDs.
- Avoid unnecessary re-renders by colocating state and splitting large components.

## Accessibility and UX

- Use semantic HTML first.
- Keep labels, roles, and focus behavior accessible for forms and interactive controls.
- Ensure keyboard accessibility for non-trivial interactions.
- Surface actionable error messages and preserve retry paths.

## Styling and UI Consistency

- Reuse existing UI primitives in `frontend/src/components/ui/*` before adding new foundations.
- Prefer existing tokens/utilities and established spacing/typography patterns.
- Keep variant APIs small and predictable for reusable components.

## Testing and Validation

- Frontend quality gates in this repository are lint and build.
- Run:
  - `pnpm run lint`
  - `pnpm run build`
- For data-flow changes, manually validate loading/error/empty and success states.

## Review Checklist

- Types are explicit and safe.
- Async states are complete.
- Query keys and hook usage are stable.
- Accessibility basics are preserved.
- Changes follow existing feature architecture.
