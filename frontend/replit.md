# AstroGen

A premium astronomical AI platform for generating, analyzing, and interpreting space imagery using deep learning models (LoRA Stable Diffusion, VAE-GAN, BLIP-2, Gemini).

## Run & Operate

- `pnpm --filter @workspace/astrogen run dev` — run the frontend (port auto-assigned)
- `pnpm --filter @workspace/api-server run dev` — run the Express API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- Required env: `DATABASE_URL` — Postgres connection string
- **Python backend**: The AstroGen Python FastAPI backend must run separately at `localhost:8001`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: React + Vite, TanStack Query, Tailwind CSS, shadcn/ui, Framer Motion, Wouter
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/astrogen/` — React + Vite frontend (premium space-themed UI)
- `artifacts/api-server/` — Express API server
- `lib/api-spec/openapi.yaml` — API contract (source of truth)
- `lib/api-client-react/src/generated/` — Generated React Query hooks
- `lib/api-zod/src/generated/` — Generated Zod schemas

## Architecture decisions

- Vite dev server proxies `/api/*` → `localhost:8001/*` (Python FastAPI backend, strips prefix)
- Vite dev server proxies `/generated/*` → `localhost:8001/generated/*` (static generated images)
- Frontend uses generated hooks from `@workspace/api-client-react` for all API calls
- Space theme is always dark — `:root` and `.dark` share identical space-inspired HSL palette
- `setBaseUrl` is not used; proxy handles routing to the Python backend transparently

## Product

AstroGen frontend with three pages:
- `/` — Full informational home page with animated starfield hero, architecture pipeline, research innovations, project stats, astronomy categories
- `/generate` — AI workspace with session sidebar, chat interface, 4 model modes (LoRA-SD, VAE-GAN, BLIP-2, Gemini), mission-control loading states
- `/gallery` — Grid gallery of all generated astronomical images

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Python backend must be running at `localhost:8001` for API calls to work (502 errors when offline are expected)
- After any OpenAPI spec change, run `pnpm --filter @workspace/api-spec run codegen` before rebuilding
- Google Fonts `@import url(...)` must be the VERY FIRST line in index.css

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
