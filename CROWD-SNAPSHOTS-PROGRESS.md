# Crowd Snapshots + Weight — Progress / Checkpoint

Goal: daily refresh guaranteed + matchday-intense crowd (snapshots 3x/day, trend arrows, crowd as ~12% ensemble vote). Loop: code → push → Actions CI → Vercel. No local installs/builds.

## Todos
- [x] `db.py`: CrowdSnapshot model + helpers (record throttled 30min, history, trend)
- [x] `engine/tips.py`: build_tip crowd_1x2 vote, weight 0.12, reason line
- [x] `server/main.py`: fetch crowd BEFORE tip, persist snapshot, attach crowdTrend, add /crowd-trend
- [x] `.github/workflows/warm.yml`: daily 6am + intraday 8-22/2h warm (hits /tips → warms + snapshots)
- [x] frontend: 15-min auto-poll + staleness badge (/ + /tips), trend arrows in CrowdBars, crowdTrend type
- [x] Verify py_compile, leave unpushed for `push`

## Status 2026-09-16
- Prior state: Vercel cron `/api/ingest` 6am daily only; in-memory caches (120s tips, 600s polymarket) wiped on cold start; crowd display-only (never moved pick).
- Design: /tips persists crowd snapshot (throttled: skip if latest <30min) → history per fixture → trend = last minus first. Crowd votes in ensemble at 0.12 weight, skipped when low_volume.
- Secrets needed for workflow: PROD_URL (e.g. https://<app>.vercel.app), CRON_SECRET only if backend sets it (currently open).
- `server/main.py` startup hook calls `init_db()` (best-effort) — Vercel deploy auto-creates `crowd_snapshots`, no manual step.

## Changed files
- (pending) `db.py`, `engine/tips.py`, `server/main.py`
- (pending) `.github/workflows/warm.yml` — NEW
- (pending) `frontend/app/lib/tips.ts`, `frontend/app/page.tsx`, `frontend/app/tips/page.tsx`, `frontend/app/components/ModelVisuals.tsx`

## Commands
- `git status --short` — explicit adds only, NEVER `git add -A` (backup tarball)
- `python3 -m py_compile db.py engine/tips.py server/main.py`
- `python -c "import db; db.init_db()"` — creates crowd_snapshots (needs DATABASE_URL; CI/prod or Neon)
- commit as Jeff-tek, `git push` only on explicit `push`

## Gotchas
- No local npm; CI gates TS.
- Snapshot writes are best-effort try/except — /tips never 500s on DB failure.
- Vercel Hobby cron limits may block intraday crons — GitHub Action is the reliable path.
- NEVER print git remote (contains PAT).

## Resume
- `git status --short` in `/root/football-model`, read this file, continue first unchecked todo.
- Delete only on explicit user confirm.
