from datetime import datetime, timezone
from scrapers.fbref import _get, _read_tables, _num, _int, LEAGUES

_VENUE = {"Home": "H", "Away": "A", "Neutral": "N"}


def fetch_team_matchlog(team_id, team_name, league, season):
    comp_id = LEAGUES[league][0]
    url = (f"https://fbref.com/en/squads/{team_id}/{season}/matchlogs/"
           f"c{comp_id}/schedule/")
    table = next(t for t in _read_tables(_get(url))
                 if {"Date", "Venue", "Opponent"}.issubset(t.columns))
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for _, r in table.iterrows():
        gf, ga = _num(r.get("GF")), _num(r.get("GA"))
        if gf is None or ga is None:
            continue
        v = str(r.get("Venue", "")).strip()
        out.append({"team_id": team_id, "team": team_name, "league": league,
                    "season": season, "date": str(r["Date"]).strip(),
                    "venue": _VENUE.get(v, v[:1]), "opponent": str(r["Opponent"]).strip(),
                    "gf": _int(gf), "ga": _int(ga),
                    "result": str(r.get("Result", "")).strip()[:1],
                    "xg_for": _num(r.get("xG")), "xg_against": _num(r.get("xGA")),
                    "possession": _num(r.get("Poss")), "scraped_at": now})
    return out
