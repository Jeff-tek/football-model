import os
from db import (init_db, upsert_matches, upsert_standings, upsert_distribution,
                upsert_team_matches, upsert_injuries, upsert_managers,
                upsert_odds, SessionLocal)
from scrapers import understat, understat_standings as ust, fpl, managers
from engine.module2_metrics import weighted_xg_deviation, weighted_form

U_SEASON = os.environ.get("CURRENT_SEASON_UNDERSTAT", "2025")
F_SEASON = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
NORM_FIELDS = ["xga_per_game", "xg_for", "xg_against", "xgdev", "form"]


def _compute_league_distributions(league, f_season):
    """Compute xgdev and form distributions from TeamMatch data."""
    from db import TeamMatch
    with SessionLocal() as s:
        teams = [r[0] for r in s.query(TeamMatch.team_id)
                 .filter(TeamMatch.league == league, TeamMatch.season == f_season)
                 .distinct().all()]
        xgdevs, forms = [], []
        for team in teams:
            rows = (s.query(TeamMatch)
                    .filter(TeamMatch.team_id == team, TeamMatch.season == f_season)
                    .order_by(TeamMatch.date.asc()).limit(10).all())
            if not rows:
                continue
            ms = [{"goals": float(r.gf or 0), "xg_for": r.xg_for if r.xg_for is not None else float(r.gf or 0),
                   "result": (r.result or "D")[:1]} for r in rows]
            xd = weighted_xg_deviation(ms)
            fm = weighted_form(ms)
            if xd is not None:
                xgdevs.append(xd)
            if fm is not None:
                forms.append(fm)

    def _dist(vals):
        if len(vals) < 2:
            return {"mean": 0.0, "std": 0.5}
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
        return {"mean": mean, "std": var ** 0.5 if var > 0 else 0.5}

    return {"xgdev": _dist(xgdevs), "form": _dist(forms)}


def run():
    init_db()
    for slug, name in understat.LEAGUES.items():
        raw = understat.fetch_league_matches(slug, U_SEASON)
        # Normalise season to FBref format across all tables
        matches = [{**m, "season": F_SEASON} for m in raw]
        upsert_matches(matches)
        standings = ust.build_standings(matches, name, F_SEASON)
        upsert_standings(standings)
        upsert_team_matches(ust.build_team_matches(matches, name, F_SEASON))
        for field in NORM_FIELDS[:3]:
            upsert_distribution(name, F_SEASON, field,
                                ust.league_distribution(standings, field))
        dists = _compute_league_distributions(name, F_SEASON)
        for field in ("xgdev", "form"):
            upsert_distribution(name, F_SEASON, field, dists[field])
        print(f"{name}: {len(standings)} teams, {len(matches)} matches, "
              f"xgdev_std={dists['xgdev']['std']:.3f}, form_std={dists['form']['std']:.3f}")

    upsert_injuries(fpl.fetch_pl_injuries(), replace_source="fpl")
    print("Managers:")
    upsert_managers(managers.fetch_all_managers())
    print("Ingest complete (Understat + Transfermarkt managers + league dists).")


if __name__ == "__main__":
    run()
