# Window View — Progress / Checkpoint

Goal: `/` + `/tips` show ESPN's current scoreboard window (sorted by date, date labels), never empty between matchdays. Loop: code → push → Actions CI → Vercel. No local installs/builds.

## Todos
- [x] `server/main.py`: remove `_is_today` gate, skip post/FT only, sort by date
- [x] `frontend/app/lib/today.ts` + `page.tsx` + `tips/page.tsx`: window sort, relabel Today headings
- [in_progress] Verify `py_compile`, leave unpushed for `push` command

## Status 2026-09-16
- Root cause: ESPN returns a matchday window, not strictly today. 2026-09-16 has zero fixtures (La Liga 3 are FT 09-15, next 4 are 09-18). Strict UTC-today filter (`1b80001`) → `[]` on both pages.
- Secondary: double date filter (backend UTC day + frontend local day) can disagree by a day on evening KOs. This revamp removes the frontend day filter; backend returns window.
- Partial-board note: `_odds()` needs all 3 legs for full board; `_engine_tip` tolerates None odds (build_tip skips None), so partials render as model-only NO BET via existing path. Kept as-is.
- Verified 2026-09-16: `py_compile` OK; live ESPN window-pre counts EPL 1 / La Liga 0 / Serie A 1 / Bundesliga 1 / Ligue 1 1 (all 09-18). `_is_today` helper left unused in server/main.py.

## Changed files
- (pending) `server/main.py` — drop today gate, skip `post`, sort tips by date
- (pending) `frontend/app/lib/today.ts` — drop sameLocalDay, sort window by date
- (pending) `frontend/app/page.tsx` — Today → window labels
- (pending) `frontend/app/tips/page.tsx` — Today's Tips → Tips labels

## Commands
- `git status --short` — verify only intended files
- `python3 -m py_compile server/main.py ingest/espn_free.py engine/tips.py`
- `git -c user.name=Jeff-tek -c user.email=75492107+Jeff-tek@users.noreply.github.com commit -m "..."`
- `git push` — only on explicit `push`
- Verify: Vercel `/` shows Sept 18 fixtures after deploy

## Gotchas
- NEVER `git add -A` (would grab backup tarball). Add explicit paths only.
- No local `npm install/build` per user loop; rely on CI typecheck.
- ESPN scoreboard = matchday window, not strictly today → empty days impossible after this change; past FT skipped via state.
- `.gitconfig` already Jeff-tek, but pass `-c` flags anyway.

## Resume
- If interrupted: `git status --short` in `/root/football-model`, read this file, continue from first unchecked todo.
- Delete this file only after user explicitly confirms done.
