# Today Revamp — Progress / Checkpoint

Goal: `/` = Today's Matches across ESPN 5, click row → tip. Local-day filter. Loop: code → push → Actions CI → Vercel. No local builds.

## Todos
- [x] `frontend/app/lib/today.ts`: getTodayMatches() fan-out 5x getTips + local-day filter
- [x] `frontend/app/components/TipCard.tsx`: extract from tips/page.tsx
- [x] `frontend/app/desk/page.tsx`: preserve Model Desk (old page.tsx)
- [x] `frontend/app/page.tsx`: rewrite as Today's Matches
- [ ] Push as Jeff-tek, exclude backup tarball

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
