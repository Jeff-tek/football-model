"""FBref replacement. Builds standings + team match logs + league
distributions purely from Understat match data (already fetched, no
Cloudflare, no extra anti-bot fight). PPDA is left null here; the engine
redistributes its weight automatically when PPDA is missing."""
from datetime import datetime, timezone

_VENUE_POINTS = {"W": 3, "D": 1, "L": 0}


def _result(gf, ga):
    if gf > ga:
        return "W"
    if gf < ga:
        return "L"
    return "D"


def build_team_matches(matches, league, season):
    """Two rows per played match (home + away perspective), matching the
    TeamMatch schema. team_id == team name so all joins stay consistent."""
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for m in matches:
        if not m.get("played"):
            continue
        hg, ag = m["home_goals"], m["away_goals"]
        hx, ax = m["home_xg"], m["away_xg"]
        date = (m["date"] or "")[:10]
        # home perspective
        out.append({"team_id": m["home_team"], "team": m["home_team"],
                    "league": league, "season": season, "date": date, "venue": "H",
                    "opponent": m["away_team"], "gf": int(hg), "ga": int(ag),
                    "result": _result(hg, ag), "xg_for": hx, "xg_against": ax,
                    "ppda": None, "possession": None, "scraped_at": now})
        # away perspective
        out.append({"team_id": m["away_team"], "team": m["away_team"],
                    "league": league, "season": season, "date": date, "venue": "A",
                    "opponent": m["home_team"], "gf": int(ag), "ga": int(hg),
                    "result": _result(ag, hg), "xg_for": ax, "xg_against": hx,
                    "ppda": None, "possession": None, "scraped_at": now})
    return out


def build_standings(matches, league, season):
    """Aggregate played matches into a league table with xG/xGA per team."""
    now = datetime.now(timezone.utc).isoformat()
    agg = {}

    def slot(team):
        return agg.setdefault(team, {"mp": 0, "xgf": 0.0, "xga": 0.0,
                                     "gf": 0, "ga": 0, "pts": 0})

    for m in matches:
        if not m.get("played"):
            continue
        h, a = slot(m["home_team"]), slot(m["away_team"])
        hg, ag = m["home_goals"], m["away_goals"]
        h["mp"] += 1; a["mp"] += 1
        h["xgf"] += m["home_xg"] or 0; h["xga"] += m["away_xg"] or 0
        a["xgf"] += m["away_xg"] or 0; a["xga"] += m["home_xg"] or 0
        h["gf"] += int(hg); h["ga"] += int(ag)
        a["gf"] += int(ag); a["ga"] += int(hg)
        h["pts"] += _VENUE_POINTS[_result(hg, ag)]
        a["pts"] += _VENUE_POINTS[_result(ag, hg)]

    ranked = sorted(agg.items(),
                    key=lambda kv: (kv[1]["pts"], kv[1]["gf"] - kv[1]["ga"]),
                    reverse=True)
    out = []
    for rank, (team, s) in enumerate(ranked, start=1):
        out.append({"league": league, "season": season, "team": team,
                    "team_id": team, "rank": rank, "matches_played": s["mp"],
                    "xg_for": round(s["xgf"], 3), "xg_against": round(s["xga"], 3),
                    "xga_per_game": round(s["xga"] / s["mp"], 4) if s["mp"] else None,
                    "points": s["pts"], "scraped_at": now})
    return out


def league_distribution(standings, field):
    vals = [r[field] for r in standings if r.get(field) is not None]
    if len(vals) < 2:
        return {"mean": None, "std": None, "n": len(vals)}
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return {"mean": mean, "std": var ** 0.5, "n": len(vals)}
