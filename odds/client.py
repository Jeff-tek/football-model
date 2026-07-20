import os, requests
from difflib import get_close_matches
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as pg_insert

ODDS_API = "https://api.the-odds-api.com/v4"
SPORT_KEYS = {"Premier League": "soccer_epl", "La Liga": "soccer_spain_la_liga",
              "Serie A": "soccer_italy_serie_a", "Bundesliga": "soccer_germany_bundesliga",
              "Ligue 1": "soccer_france_ligue_one",
              "Russian Premier League": "soccer_russia_premier_league"}


def fetch_h2h_odds(league):
    key = os.environ.get("ODDS_API_KEY")
    sport = SPORT_KEYS.get(league)
    if not key or not sport:
        return []
    r = requests.get(f"{ODDS_API}/sports/{sport}/odds",
                     params={"apiKey": key, "regions": "uk,eu",
                             "markets": "h2h", "oddsFormat": "decimal"}, timeout=20)
    if r.status_code != 200:
        return []
    out = []
    for ev in r.json():
        best = {}
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk["key"] != "h2h":
                    continue
                for oc in mk["outcomes"]:
                    if oc["price"] > best.get(oc["name"], 0):
                        best[oc["name"]] = oc["price"]
        out.append({"home_team": ev["home_team"], "away_team": ev["away_team"],
                    "commence": ev["commence_time"], "prices": best})
    return out


def odds_for_fixture(league, home_team, away_team):
    from db import SessionLocal, Odds
    with SessionLocal() as s:
        row = s.query(Odds).filter(
            Odds.league == league, Odds.home_team == home_team,
            Odds.away_team == away_team, Odds.market == "h2h"
        ).first()
        if row:
            return {"home": row.home_price, "away": row.away_price}
    for ev in fetch_h2h_odds(league):
        if ev["home_team"] == home_team and ev["away_team"] == away_team:
            p = ev["prices"]
            return {"home": p.get(home_team), "away": p.get(away_team)}
    return {}


def _norm_team(odds_name, known_teams):
    """Fuzzy-match an odds API team name against known canonical names."""
    if odds_name in known_teams:
        return odds_name
    matches = get_close_matches(odds_name, known_teams, n=1, cutoff=0.5)
    if matches:
        return matches[0]
    # Try normalized comparison (lowercase, strip common prefixes)
    odds_lower = odds_name.lower().replace("fc ", "").replace("ac ", "").replace("rc ", "")
    for kt in known_teams:
        if odds_lower in kt.lower() or kt.lower() in odds_lower:
            return kt
    return odds_name  # unrecognized — will be a placeholder


def store_odds_for_league(league, session=None):
    from db import Match, Odds, Standing, SessionLocal

    evs = fetch_h2h_odds(league)
    if not evs:
        return 0

    close_session = session is None
    s = session or SessionLocal()
    try:
        fbref = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
        known = {r[0] for r in s.query(Standing.team)
                  .filter(Standing.league == league, Standing.season == fbref).all()}

        stored = 0
        all_odds_teams = set()
        for ev in evs:
            ht = _norm_team(ev["home_team"], known)
            at = _norm_team(ev["away_team"], known)
            all_odds_teams.add(ht)
            all_odds_teams.add(at)

            match = s.query(Match).filter(
                Match.league == league,
                Match.home_team == ht, Match.away_team == at
            ).first()
            mid = match.understat_match_id if match else None

            prices = ev["prices"]
            hp = prices.get(ev["home_team"], prices.get(ht))
            ap = prices.get(ev["away_team"], prices.get(at))
            if not hp or not ap:
                continue

            payload = {
                "understat_match_id": mid, "market": "h2h",
                "league": league, "home_team": ht, "away_team": at,
                "home_price": hp, "away_price": ap,
                "fetched_at": datetime.now(timezone.utc),
            }
            stmt = pg_insert(Odds).values(**payload)
            stmt = stmt.on_conflict_do_update(
                index_elements=["league", "home_team", "away_team", "market"],
                set_={"understat_match_id": stmt.excluded.understat_match_id,
                      "home_price": stmt.excluded.home_price,
                      "away_price": stmt.excluded.away_price,
                      "fetched_at": stmt.excluded.fetched_at})
            s.execute(stmt)
            stored += 1

        for team in all_odds_teams:
            if team not in known:
                stmt = pg_insert(Standing).values(
                    league=league, season=fbref, team=team,
                    team_id=team, rank=0, matches_played=0,
                    xg_for=0.0, xg_against=0.0, xga_per_game=0.0, points=0,
                )
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["league", "season", "team"])
                s.execute(stmt)

        s.commit()
        return stored
    finally:
        if close_session:
            s.close()


def fetch_and_store_all_odds():
    total = 0
    for league in SPORT_KEYS:
        cnt = store_odds_for_league(league)
        print(f"  {league}: {cnt} odds stored")
        total += cnt
    return total
