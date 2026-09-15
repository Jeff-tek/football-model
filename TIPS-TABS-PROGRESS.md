# League Tabs Progress (crash-safe checkpoint)

Date: 2026-09-15. Delivery loop: code → push → Actions CI → Vercel. No local installs.

## Request
Tabs at top showing available tips per league. Today selecting a league shows only one match — user wants to see what's available in each league.

## Findings
- `/tips?league=X` is per-league; page only ever fetched the selected league (dropdown).
- "Only one match" is data-driven: only fixtures with DraftKings 1X2 odds render. Tabs expose counts but can't invent fixtures.
- Fix is frontend-only: fetch all 6 leagues once (`Promise.allSettled`, server caches 120s), tab bar with count badges, record all leagues' picks to the P&L ledger.

## Todos
- [x] page.tsx all-league fetch + tabs — CI (pushed `4fb63b8`)
- [x] globals.css league-tabs styles — CI (pushed `4fb63b8`)
- [x] Push as Jeff-tek — commit `4fb63b8`, pushed `main -> main` 2026-09-15

## Changed files
- frontend/app/tips/page.tsx (tabs + all-league load)
- frontend/app/globals.css (tab styles)

## Commands
- `git -C /root/football-model status --short`
- push only on explicit user go-ahead (auto-proceed only under TODO CONTINUATION directive)

## Gotchas
- Russian Premier League has no ESPN free coverage → tab shows 0, empty message.
- Slowest league gates initial render (allSettled); Refresh reloads all six.
- Resume: re-read this file + `git status`, continue at first unchecked todo.
