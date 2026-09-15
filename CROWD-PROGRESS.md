# Crowd layer (Polymarket + line movement) — Progress / Checkpoint

Goal: each card shows crowd H/D/A (Polymarket public money) next to model probs
+ DraftKings open→close line move. Loop: code → push → Vercel. No local builds.

## Todos
- [x] `ingest/polymarket_free.py` — NEW (10-min cache, date-match, low-volume flag, never raise)
- [x] `ingest/espn_free.py` — open lines + `decimal_to_american`
- [x] `server/main.py` — crowd block + lineMove + reasons + source
- [x] Frontend `Tip` + `TipCard` + CSS
- [x] Tests + live verify (see below)
- [ ] Push as Jeff-tek

## Changed files
- NEW `ingest/polymarket_free.py`, `tests/test_polymarket_free.py`, `CROWD-PROGRESS.md`
- MOD `ingest/espn_free.py` (_odds gains `open`, + `decimal_to_american`),
  `server/main.py` (crowd/lineMove/reasons/sources), `frontend/app/lib/tips.ts`,
  `frontend/app/components/TipCard.tsx` (crowd box), `frontend/app/globals.css`,
  `tests/test_espn_free.py`

## Verified 2026-09-15 live
- Suites: 8+4+4+32+27 all pass, py_compile OK.
- Crowd live: Rayo-Espanyol 40.5/28.5/31.5 (thin draw leg → flagged),
  Elche-Madrid away 81.5% deep market, Brentford-Chelsea covered (thin → flagged),
  Alaves-Valencia no market → graceful None.
- Steam live: Rayo home +100→+140, Alaves home +125→-145, Elche-Madrid away -295→-500.
- Parser fix: Polymarket returns outcomes/prices as JSON-encoded strings.

## Commands
- `git add <explicit paths>` — NEVER `git add -A` (backup tarball)
- `git -c user.name=Jeff-tek -c user.email=75492107+Jeff-tek@users.noreply.github.com commit -m "..."`
- `git push`

## Gotchas
- Polymarket coverage gaps (esp. smaller/older-snapshot matches) → "no crowd market", never blocks tip.
- Thin markets (<$5k leg volume) → low-volume flag.
- Same fuzzy club matcher as openmodel (shared _norm).
- Pundit quotes deliberately OUT (brittle scraping, gray ToS) — links only, deferred.

## Resume
- `git status --short` in /root/football-model, read this file, continue first unchecked todo.
- Delete only on explicit user confirmation.
