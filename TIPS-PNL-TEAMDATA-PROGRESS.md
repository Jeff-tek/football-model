# Tips P&L + Team-Data Progress (crash-safe checkpoint)

Date: 2026-09-15. Delivery loop: code → push → Actions CI → Vercel. No local installs.

## Request
1. Monthly P&L: rolling 30d figure (Sep 15 → Oct 15) showing profitability of picks.
2. Team data side-by-side beside duel bars (CrowdBars) + prob cells — spider/radar untouched, league-specific.

## Findings (grounding)
- No bet-history store exists. `/tips` (server/main.py) is ephemeral from ESPN scoreboard; tips vanish when odds go stale. DB (db.py) has matches/standings/odds but NO picks/bets table.
- Decision: frontend localStorage ledger `tips-ledger-v1` (no migration, works without DATABASE_URL). Flat 1u stake. Units use 1X2 book odds when pick is Home/Draw/Away; Over/BTTS/DC have no free book odds → win-rate only, excluded from units with note.
- Settlement: `/live` returns post-state scores. PnLBar fetches live boards across leagues, grades picks via pure `gradePick`.
- Team data: `ingest/espn_free.fetch_standings` gives rank/points/W-D-L/GF-GA per league slug but `/tips` never includes it. Fix: `_standings_map` join in server/main.py → `teamMeta: {home, away}` per tip.

## Todos
- [x] Explore/map storage + UI
- [x] server/main.py teamMeta — py_compile
- [x] lib/ledger.ts + PnLBar — CI typecheck (pending CI run)
- [x] TeamDuel + TipCard layout + page wiring + CSS — CI (pending CI run)
- [x] Push as Jeff-tek <75492107+Jeff-tek@users.noreply.github.com> — commit `0985efe`, pushed `main -> main` 2026-09-15

## Changed files
- server/main.py (teamMeta)
- frontend/app/lib/tips.ts (TeamMeta type)
- frontend/app/lib/ledger.ts (NEW)
- frontend/app/components/PnLBar.tsx (NEW)
- frontend/app/components/TeamDuel.tsx (NEW)
- frontend/app/components/TipCard.tsx (duel-row layout)
- frontend/app/tips/page.tsx (PnLBar + recordTips)
- frontend/app/globals.css (pnl + duel-row + team styles)

## Commands
- `python3 -m py_compile server/main.py` (stdlib only)
- `git -C /root/football-model status --short`
- `git -C /root/football-model log --oneline -3`
- push (no commit without explicit ask — user already uses push loop; confirm before push)

## Gotchas
- ESPN standings team names must join case-insensitively; missing → null (render form/xG fallback).
- CrowdBars returns null without crowd data — duel-row CSS must let TeamDuel go full width.
- No local frontend typecheck per user loop — rely on CI; keep types terse and exact.
- Resume: if interrupted, re-read this file + `git status`, continue at first unchecked todo.
