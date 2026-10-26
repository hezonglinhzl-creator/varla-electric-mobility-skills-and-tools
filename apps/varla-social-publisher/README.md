# Varla Social Publisher

Local-first operations system for scheduling official-API publication to Varla's Instagram, Facebook and TikTok accounts.

## Current status

Phase-one foundation: domain model, Prisma schema, dashboard, validation API, BullMQ worker contract, mock adapter, Docker topology and tests. Real Meta/TikTok publishing is intentionally not represented as complete; see `BLOCKERS.md`.

## Local start

Requirements: Node.js 22 LTS, npm, FFmpeg/ffprobe, Redis. Docker Desktop is the easiest way to provide Redis and MinIO.

1. Copy `.env.example` to `.env` and replace all secrets.
2. Run `npm install`.
3. Run `npm run db:generate` and `npm run db:push`.
4. Run `npm run dev`, then open `http://localhost:3000`.
5. In a second terminal set `RUN_WORKER=true` and run `npm run worker`.

With Docker installed: `docker compose up --build`.

## Verification

Run `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build`.

The health endpoint is `GET /api/health`; it reports HTTP 503 until database, Redis, storage and worker heartbeat are configured. This is deliberate and prevents a visually healthy UI from hiding unavailable infrastructure.

## API safety

Only official OAuth and platform APIs are permitted. Never submit localhost media URLs. Tokens and authorization headers must be redacted. Meta Graph API version is controlled by `META_GRAPH_API_VERSION`; before changing it, compare the official changelog, run adapter contract tests, then test with platform test accounts. Authentication errors are non-retryable; transient jobs use at most three total attempts with exponential backoff.
