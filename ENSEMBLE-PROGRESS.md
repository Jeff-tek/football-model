# Ensemble (Poisson + Elo + OpenModel) — Progress / Checkpoint

Goal: safest pick (max prob across 1X2/DC/O-U/BTTS) backed by 3 voting 1X2 opinions:
our Poisson-form, ported Elo (theopenmodel math, MIT), theopenmodel published
predictions (CC BY 4.0, attributed). Loop: code → push → Vercel. No local builds.

## Todos
- [x] Confirm predictions.csv + elo-ratings.csv schemas (columns, slugs)
- [x] `ingest/openmodel_free.py` — NEW fetcher (6h cache, normalize, stale rejection, never raise)
- [x] `engine/elo.py` — NEW port of theopenmodel lib/model.ts (credited)
- [x] `engine/tips.py` — ensemble 1X2, max-prob pick, agreement-gated verdict, numeric confidence
- [x] `server/main.py` — thread through + attribution source link
- [x] Frontend `Tip` type + `TipCard` (DC/Under rows, numeric confidence)
- [x] Tests + live 7/7 verify (see below)
- [ ] Push as Jeff-tek

## Changed files
- NEW `ingest/openmodel_free.py`, `engine/elo.py`, `tests/test_elo.py`, `tests/test_openmodel_free.py`, `ENSEMBLE-PROGRESS.md`
- MOD `engine/tips.py` (ensemble + safest pick), `server/main.py` (thread + attribute),
  `frontend/app/lib/tips.ts` (DC/U2.5/models), `frontend/app/components/TipCard.tsx`,
  `frontend/app/tips/page.tsx` (dedupes to shared card), `tests/test_tips.py`

## Verified 2026-09-15 live
- Suites: test_elo 8/8, test_openmodel_free 4/4, test_tips 32/32, test_espn_free 25/25, py_compile OK.
- 7/7 matches tip end-to-end. La Liga gets 3 votes (elo+openmodel+poisson);
  Sep-18 matches get 2 (openmodel feed ends Sep 16 → graceful skip).
- Picks cut markets: 12, BTTS No, X2, Over 2.5, 1X. Split-gate seen live
  (Alaves BTTS No 83.8% capped to MARGINAL).

## Commands
- `git add <explicit paths>` — NEVER `git add -A` (backup tarball)
- `git -c user.name=Jeff-tek -c user.email=75492107+Jeff-tek@users.noreply.github.com commit -m "..."`
- `git push`
- Verify live: PYTHONPATH=. scripts + Vercel cards

## Gotchas
- Their ρ sign convention is opposite ours — keep constants sealed in engine/elo.py.
- ESPN names ≠ OpenModel names (Rayo vs Rayo Vallecano) → normalize + fuzzy, skip on mismatch.
- Snapshot may be stale (Sep 9 seen) → reject rows not pre-kickoff; stale never votes.
- OpenModel feed failure must NEVER break our tip (fallback to own models).
- CC BY 4.0 → credit "The Open Model (theopenmodel.com)" on cards.

## Resume
- `git status --short` in /root/football-model, read this file, continue first unchecked todo.
- Delete only on explicit user confirmation.
