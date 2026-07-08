import os
from db import (init_db, upsert_matches, upsert_standings, upsert_distribution,
                upsert_team_matches, upsert_injuries)
from scrapers import understat, fbref, fbref_matchlogs, fpl

U_SEASON = os.environ.get("CURRENT_SEASON_UNDERSTAT", "2025")
F_SEASON = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
NORM_FIELDS = ["xga_per_game", "xg_for", "xg_against"]


def run():
    init_db()
    for slug in understat.LEAGUES:
        upsert_matches(understat.fetch_league_matches(slug, U_SEASON))
        print(f"understat {understat.LEAGUES[slug]}: ok")
    for league in fbref.LEAGUES:
        table = fbref.fetch_standings(league, F_SEASON)
        upsert_standings(table)
        for field in NORM_FIELDS:
            upsert_distribution(league, F_SEASON, field,
                                fbref.league_distribution(table, field))
        for t in table:
            if t.get("team_id"):
                upsert_team_matches(fbref_matchlogs.fetch_team_matchlog(
                    t["team_id"], t["team"], league, F_SEASON))
        print(f"fbref {league}: {len(table)} teams")
    upsert_injuries(fpl.fetch_pl_injuries(), replace_source="fpl")
    print("Nightly ingest complete.")


if __name__ == "__main__":
    run()
