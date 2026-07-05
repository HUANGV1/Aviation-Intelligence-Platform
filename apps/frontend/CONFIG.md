# Frontend config files

## package.json

**Purpose:** npm package manifest for the Next.js frontend (scripts, dependencies).

**Interactions:** Run via `npm run dev` / `build` / `start` from `apps/frontend/`. Pulls in Next.js, React, and TypeScript used by everything under `src/`.

## tsconfig.json

**Purpose:** TypeScript compiler options for the frontend.

**Interactions:** Used by `next build` and the IDE. Enables strict mode and the `@/*` → `src/*` path alias used by `page.tsx`, `lib/api.ts`, and `components/`.
