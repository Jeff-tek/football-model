"""Free ESPN soccer ingest — pure fetch+parse, stdlib+requests only.

Endpoints (unofficial, may change):
  scoreboard: site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard
  schedule:   site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{id}/schedule?season=2026
  standings:  site.api.espn.com/apis/v2/sports/soccer/{slug}/standings
"""
import json
import logging
import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_BASE = "https://site.api.espn.com/apis/v2/sports/soccer"
TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (football-model/1.0)"}
log = logging.getLogger(__name__)


def _fix_pvt(obj):
    """ESPN sometimes serves .pvt hosts; normalize to .com recursively."""
    if isinstance(obj, dict):
        return {k: _fix_pvt(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fix_pvt(v) for v in obj]
    if isinstance(obj, str):
        return obj.replace(".pvt.", ".com.")
    return obj


def _get(url, params=None):
    """GET JSON; log + return None on any failure (never raise)."""
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        return _fix_pvt(r.json())
    except Exception as e:
        log.warning("espn fetch failed %s: %s", url, e)
        return None


def _to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _competitors(comp):
    out = {}
    for c in comp.get("competitors", []) or []:
        team = c.get("team", {}) or {}
        side = c.get("homeAway", "away")
        out[side] = {
            "id": str(team.get("id", "")),
            "name": team.get("displayName") or team.get("shortDisplayName") or "",
            "score": _to_int(c.get("score")),
        }
    return out


def _odds(comp):
    for o in comp.get("odds", []) or []:
        for d in o.get("details", []) or []:
            price = d.get("price", {}) or {}
            return {"provider": (d.get("provider", {}) or {}).get("name", ""),
                    "home": _to_float(price.get("home")),
                    "away": _to_float(price.get("away")),
                    "draw": _to_float(price.get("draw"))}
    return {}


def _parse_event(ev):
    comps = ev.get("competitions", []) or []
    if not comps:
        return None
    comp = comps[0]
    teams = _competitors(comp)
    if "home" not in teams or "away" not in teams:
        return None
    status = (comp.get("status", {}) or {}).get("type", {}) or {}
    return {
        "id": str(ev.get("id", "")),
        "date": ev.get("date", ""),
        "home": teams["home"]["name"],
        "away": teams["away"]["name"],
        "home_id": teams["home"]["id"],
        "away_id": teams["away"]["id"],
        "home_score": teams["home"]["score"],
        "away_score": teams["away"]["score"],
        "state": status.get("state", "pre"),
        "detail": status.get("shortDetail", ""),
        "odds": _odds(comp),
    }


def fetch_scoreboard(league_slug):
    """Live + upcoming matches for a league slug (eng.1, esp.1, ...)."""
    data = _get(f"{BASE}/{league_slug}/scoreboard")
    if not data:
        return []
    return [m for m in (_parse_event(ev) for ev in data.get("events", []) or []) if m]


def fetch_team_schedule(team_id, league_slug="eng.1", season="2026"):
    """Played matches for a team (form source). Team IDs are global in ESPN."""
    data = _get(f"{BASE}/{league_slug}/teams/{team_id}/schedule",
                params={"season": season})
    if not data:
        return []
    out = []
    for ev in data.get("events", []) or []:
        m = _parse_event(ev)
        if m and m["state"] == "post":
            out.append({**m, "played": True})
    return out


def fetch_standings(league_slug):
    """Standings table for a league slug."""
    data = _get(f"{STANDINGS_BASE}/{league_slug}/standings")
    if not data:
        return []
    rows = []
    for child in data.get("children", []) or []:
        entries = ((child.get("standings", {}) or {}).get("entries", []) or [])
        for i, e in enumerate(entries, start=1):
            team = e.get("team", {}) or {}
            stats = {s.get("name"): s.get("value") for s in e.get("stats", []) or []}
            rows.append({
                "rank": i,
                "team": team.get("displayName") or team.get("shortDisplayName") or "",
                "team_id": str(team.get("id", "")),
                "points": _to_int(stats.get("points")),
                "matches_played": _to_int(stats.get("gamesPlayed")),
                "wins": _to_int(stats.get("wins")),
                "losses": _to_int(stats.get("losses")),
                "ties": _to_int(stats.get("ties")),
                "gf": _to_int(stats.get("pointsFor")),
                "ga": _to_int(stats.get("pointsAgainst")),
            })
    return rows