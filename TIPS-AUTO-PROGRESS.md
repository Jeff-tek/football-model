# Auto-Pull Tips — Progress / Checkpoint

Goal: free $0 auto-pull live soccer + grounded tips (O/U, BTTS, 1X2; props = manual proxy), visitable on phone via Vercel. No local builds. Loop: code → push → Actions CI → Vercel.

## Todos
- [x] Map ingest/engine/server/frontend inventory
- [x] Ingest: `ingest/espn_free.py` + `ingest/openliga_free.py` (free ESPN/OpenLigaDB pull, tested)
- [x] Engine: `engine/tips.py` (Poisson + Dixon-Coles, pure functions, tested)
- [x] Server: `/tips` endpoint — GET /tips?league=La Liga composing espn_free + engine/tips
- [x] Frontend: `app/tips/page.tsx` mobile cards + refresh + league select + disclaimer
- [ ] Verify: CI typecheck + push-ready (no local build)
- Verified 12:25 UTC: py_compile OK, test_espn_free 21/21, test_tips 29/29, LSP unavailable (declined). UI agent final pass still running.
- Verified final 12:45 UTC: all 3 builders done (ingest, engine retry, UI). COMPILE-OK, 21/21 + 29/29. Files: ingest/espn_free.py, ingest/openliga_free.py, engine/tips.py, server/main.py (/tips+/live+/form), frontend/app/tips/page.tsx, frontend/app/lib/tips.ts. Push-ready, NOT committed (awaiting user).

## Completed 2026-09-15

### Backend: `server/main.py` (additive only)
- `GET /tips?league=La Liga` — composes `ingest/espn_free.fetch_scoreboard` (parsed events) + `engine/tips.build_tip` (Poisson + Dixon-Coles with form from `fetch_team_schedule`)
- Defensive imports: if `ingest/espn_free` missing → raw ESPN direct fetch; if `engine/tips` missing or form unavailable → `_simple_tip` fallback (simplified Poisson from DraftKings moneyline)
- `_team_avg()` — last-5 goals for/against from ESPN team schedules
- `_simple_tip()` — fallback Poisson 1X2/O2.5/BTTS + edge + verdict
- `_engine_tip()` — composes build_tip, maps output to response shape (confidence LOW/MED/HIGH → 40/65/85)
- Uses existing `_cached` (120s TTL) + `_espn_slug` helpers
- League allowlist via `LEAGUE_SLUGS`; leagues without ESPN coverage return empty tips (not error)
- Returns: `{league, as_of, ttl, cron, tips: [{home, away, date, probs, fair, edge, pick, verdict, reasons, confidence, sources, homeForm, awayForm, homeXG, awayXG, bookOdds}]}`

### Frontend: `app/tips/page.tsx` (143 lines, "use client")
- `TipCard`: matchup, form line, xG, 1X2/O2.5/BTTS probs with fair comparison, edge badge, verdict pill, reasons, sources, confidence
- `TipsPage`: league select + refresh button, loading/empty/error states
- Props manual-check checklist (lineup, goalscorer form, bookmaker odds)
- Responsible gambling disclaimer with BeGambleAware link
- TTL + cron metadata display

### Frontend: `app/lib/tips.ts` (34 lines)
- `Tip` and `TipsResponse` types matching backend
- `getTips(league)` with `NEXT_PUBLIC_API_URL` fallback

### CSS: `app/globals.css` (+55 lines)
- 2 new variables: `--card-bg`, `--verdict-marginal` + `--verdict-marginal-soft`
- 23 new utility classes: `.tips-head`, `.tips-controls`, `.refresh`, `.tips-meta`, `.tips-list`, `.tip-card`, `.tip-top`, `.tip-matchup`, `.tip-meta`, `.tip-band`, `.tip-pickbox`, `.prob-grid`, `.prob-cell`, `.prob-label`, `.prob-val`, `.edge-badge`, `.verdict-pill`, `.tip-reasons`, `.tip-reason`, `.source-links`, `.source-link`, `.disclaimer`, `.props-note`
- Mobile-first: single column, system font, oklch vars throughout

## Files changed (this session)
- `server/main.py` — added /tips endpoint + helpers (additive)
- `frontend/app/tips/page.tsx` — NEW: tips page
- `frontend/app/lib/tips.ts` — NEW: types + fetch helper
- `frontend/app/globals.css` — added tips CSS (append only)
- `TIPS-AUTO-PROGRESS.md` — this file

## Pre-existing untracked (prior session, not touched)
- `ingest/espn_free.py`, `ingest/openliga_free.py` — free ESPN/OpenLigaDB ingest
- `engine/tips.py` — Poisson + Dixon-Coles engine
- `tests/test_espn_free.py`, `tests/test_tips.py` — mocked tests

## Not changed (no breakage)
- `frontend/app/page.tsx`, `slip.tsx`, `lib/api.ts`, `layout.tsx` — untouched
- `api/index.py`, `vercel.json` — untouched
- `engine/*` (except tips.py pre-existing), `ingest/run_all.py` — untouched

## Verification
- `python3 -m py_compile server/main.py` — PASS
- Poisson math validated — 1X2 sums to ~1.0
- `_team_avg` validated with Rayo/Espanyol form records
- `build_tip` composition validated end-to-end with mocked ESPN schedules (Rayo-Espanyol → away BET +24.9%, fallback path works)
- Manual TypeScript review — `O2.5` uses bracket notation, no `as any`, no `ts-ignore`
- LSP not available locally — CI typecheck via GitHub Actions

## Next step
- `git add -A && git commit` then `git push` → GitHub Actions CI → Vercel deploy
- Verify `https://<vercel>/tips` shows La Liga cards
- If ingest/espn_free.py or engine/tips.py change, /tips auto-composes them (defensive imports)