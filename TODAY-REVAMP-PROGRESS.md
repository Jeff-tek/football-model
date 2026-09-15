# Today Revamp — Progress / Checkpoint

Goal: `/` = Today's Matches across ESPN 5, click row → tip. Local-day filter. Loop: code → push → Actions CI → Vercel. No local builds.

## Todos
- [x] `frontend/app/lib/today.ts`: getTodayMatches() fan-out 5x getTips + local-day filter
- [x] `frontend/app/components/TipCard.tsx`: extract from tips/page.tsx
- [x] `frontend/app/desk/page.tsx`: preserve Model Desk (old page.tsx)
- [x] `frontend/app/page.tsx`: rewrite as Today's Matches
- [x] Push as Jeff-tek, exclude backup tarball

## Status 2026-09-15 ~13:0x UTC
- Committed `4bff8e8` as Jeff-tek, pushed `main -> main` (repo moved Jeff-tek/football-model, push followed redirect OK).
- `gh run list` empty — no Actions workflows in repo, so no CI to wait for; Vercel deploys on push.
- Working tree clean except untracked `host-uncommitted-backup-2026-08-17.tar.gz` (intentionally never added).

## Fix 2026-09-15 — empty tips root causes (2 bugs)
1. `ingest/espn_free.py` custom `User-Agent: Mozilla/5.0 (football-model/1.0)` → ESPN 403 Access Denied
   (requests default UA returns 200; verified per-league). Dropped custom HEADERS in
   `espn_free._get` + `openliga_free._get`. Test `test_scoreboard_user_agent` → `test_scoreboard_no_custom_user_agent`.
2. `_odds` parsed a stale schema (`odds[].details[].price`) — live ESPN uses
   `odds[].moneyline.{home,draw,away}.{close,open}.odds` (American) + string `details`
   (crashed with AttributeError → /tips 500/empty). Rewrote `_odds` + new `american_to_decimal`,
   added `home_form`/`away_form` from competitor `form`. `server/main.py`: parsed branch uses
   new form fields; raw fallback converts moneyLine via local `_to_dec` + homeAway mapping.
- Verified live: eng/esp/ita/ger/fra all parse with decimal odds + form (La Liga has 2 today).
- Tests: test_espn_free 24/24, test_tips 29/29, py_compile OK.

## Changed files
- (pending) `frontend/app/lib/today.ts` — NEW
- (pending) `frontend/app/components/TipCard.tsx` — NEW
- (pending) `frontend/app/desk/page.tsx` — NEW (moved old home)
- (pending) `frontend/app/page.tsx` — REWRITE

## Commands
- `git status --short` — verify only intended files + exclude `host-uncommitted-backup-2026-08-17.tar.gz`
- `git add frontend/app/page.tsx frontend/app/desk/page.tsx frontend/app/lib/today.ts frontend/app/components/TipCard.tsx TODAY-REVAMP-PROGRESS.md`
- `git -c user.name=Jeff-tek -c user.email=75492107+Jeff-tek@users.noreply.github.com commit -m "..."`
- `git push`
- Verify: `gh run list --limit 3`, check Vercel `/`

## Gotchas
- ESPN scoreboard = matchday window, not strictly today → empty days are normal, show empty state.
- No-odds matches skipped by /tips → show "no odds yet" only if backend returns them; v1 just shows tips with odds.
- ESPN dates UTC ISO → compare via local YMD (getFullYear/getMonth/getDate).
- `.gitconfig` already Jeff-tek, but pass `-c` flags anyway to guarantee identity.
- NEVER `git add -A` (would grab backup tarball). Add explicit paths only.
- No local `npm install/build` per user loop; rely on CI typecheck.

## Resume
- If interrupted: `git status --short` in `/root/football-model`, read this file, continue from first unchecked todo.
- Delete this file only after user explicitly confirms done.
