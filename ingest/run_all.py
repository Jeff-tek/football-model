import os
from db import (init_db, upsert_matches, upsert_standings, upsert_distribution,
                upsert_team_matches, upsert_injuries)
from scrapers import understat, understat_standings as ust, fpl

U_SEASON = os.environ.get("CURRENT_SEASON_UNDERSTAT", "2025")
F_SEASON = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
NORM_FIELDS = ["xga_per_game", "xg_for", "xg_against"]


def run():
    init_db()
    for slug, name in understat.LEAGUES.items():
        matches = understat.fetch_league_matches(slug, U_SEASON)
        upsert_matches(matches)
        # standings + team logs + distributions, all from Understat data
        standings = ust.build_standings(matches, name, F_SEASON)
        upsert_standings(standings)
        upsert_team_matches(ust.build_team_matches(matches, name, F_SEASON))
        for field in NORM_FIELDS:
            upsert_distribution(name, F_SEASON, field,
                                ust.league_distribution(standings, field))
        print(f"{name}: {len(standings)} teams, {len(matches)} matches")
    upsert_injuries(fpl.fetch_pl_injuries(), replace_source="fpl")
    print("Ingest complete (Understat-only, FBref bypassed).")


if __name__ == "__main__":
    run()
