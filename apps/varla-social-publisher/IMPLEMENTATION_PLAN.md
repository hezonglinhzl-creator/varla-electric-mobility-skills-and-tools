# Varla Social Publisher — Implementation Plan

## Architecture

Local-first npm-workspaces monorepo. Next.js owns the authenticated operations UI and HTTP API. BullMQ owns delayed publication and retries. Prisma is the persistence boundary. Platform adapters implement one interface so mock, Meta, and TikTok transports can be swapped without changing orchestration. Media bytes live behind a StorageProvider; database rows store metadata and object keys only.

## Directory structure

```text
apps/web              Next.js admin UI and API routes
apps/worker           BullMQ scheduler/publisher worker
packages/core         domain state machine, validation, timezone, errors
packages/platform-meta    Meta adapter (phase 2)
packages/platform-tiktok  TikTok adapter (phase 3)
prisma                database schema
```

## Milestones

- [x] M0: architecture, repository and environment contract
- [x] M1: Prisma schema and domain state machine
- [ ] M2: secure single-admin session
- [ ] M3: upload, ffprobe validation, thumbnail and deduplication
- [ ] M4: content editor, immutable approval snapshot and UTC scheduling
- [x] M5: BullMQ worker and mock adapter foundation
- [ ] M6: Docker Compose, health checks and phase-one acceptance
- [ ] M7: Meta OAuth and real Instagram/Facebook publishing
- [ ] M8: TikTok OAuth, draft/direct posting and audit preparation
- [ ] M9: webhooks, recovery, security audit and production runbook

## Verification gate

Every milestone must pass lint, TypeScript checking and tests. Real platform work is never marked complete without credentials and a recorded, redacted API response. Blockers go in `BLOCKERS.md`.
