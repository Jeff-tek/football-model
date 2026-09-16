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
# NOTE: send no custom User-Agent — ESPN returns 403 Access Denied for
# custom UAs but allows requests' default (verified 2026-09-15).
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
        r = requests.get(url, params=params, timeout=TIMEOUT)
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


def _dec_or_none(f):
    return round(f, 3) if isinstance(f, float) and f > 1 else None


def decimal_to_american(dec):
    """Decimal odds → American string (+135 / -110). None when unusable."""
    try:
        profit = float(dec) - 1.0
    except (TypeError, ValueError):
        return None
    if profit >= 1.0:
        return f"+{round(profit * 100):.0f}"
    if profit > 0:
        return f"-{round(100 / profit):.0f}"
    return None


def american_to_decimal(v):
    """American odds (+135, -110, 'EVEN') → decimal. Decimal input passes through."""
    if isinstance(v, str):
        s = v.strip().upper()
        if s in ("EVEN", "EV"):
            return 2.0
        if s[:1] in ("+", "-"):
            v = _to_int(s)
            if v is None:
                return None
        else:
            return _dec_or_none(_to_float(s))
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and abs(v) < 100:
        return _dec_or_none(float(v))
    ml = _to_int(v)
    if not ml:
        return None
    return round(1 + ml / 100, 3) if ml > 0 else round(1 + 100 / abs(ml), 3)


def _score(c):
    """Competitor score: plain string on scoreboards, {value/displayValue} dict on schedules."""
    s = c.get("score")
    if isinstance(s, dict):
        return _to_int(s.get("value", s.get("displayValue")))
    return _to_int(s)


def _competitors(comp):
    out = {}
    for c in comp.get("competitors", []) or []:
        if not isinstance(c, dict):
            continue
        team = c.get("team", {}) or {}
        side = c.get("homeAway", "away")
        out[side] = {
            "id": str(team.get("id", "")),
            "name": team.get("displayName") or team.get("shortDisplayName") or "",
            "score": _score(c),
            "form": c.get("form", "") or "",
        }
    return out


def _ml(moneyline, side):
    """Close American line preferred, open as fallback → decimal."""
    if not isinstance(moneyline, dict):
        return None
    leg = moneyline.get(side) or {}
    if not isinstance(leg, dict):
        return None
    for key in ("close", "open"):
        node = leg.get(key) or {}
        if isinstance(node, dict) and node.get("odds") is not None:
            dec = american_to_decimal(node.get("odds"))
            if dec:
                return dec
    return None


def _open_lines(moneyline):
    """Opening decimals per side (close equivalents live in _odds); Nones when absent."""
    out = {}
    for side in ("home", "draw", "away"):
        dec = None
        if isinstance(moneyline, dict):
            leg = moneyline.get(side) or {}
            if isinstance(leg, dict):
                node = leg.get("open") or {}
                if isinstance(node, dict) and node.get("odds") is not None:
                    dec = american_to_decimal(node.get("odds"))
        out[side] = dec
    return out


def _odds(comp):
    """Decimal 1X2 from DraftKings moneyline; {} when absent/incomplete."""
    entries = comp.get("odds") or []
    if not isinstance(entries, list):
        return {}
    dicts = [o for o in entries if isinstance(o, dict)]
    dk = next((o for o in dicts if (o.get("provider") or {}).get("name") == "DraftKings"), None)
    cands = ([dk] + [o for o in dicts if o is not dk]) if dk else dicts
    for o in cands:
        ml = o.get("moneyline")
        h, d, a = _ml(ml, "home"), _ml(ml, "draw"), _ml(ml, "away")
        if h and d and a:
            return {"provider": (o.get("provider") or {}).get("name", ""),
                    "home": h, "draw": d, "away": a,
                    "open": _open_lines(ml)}
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
        "home_form": teams["home"].get("form", ""),
        "away_form": teams["away"].get("form", ""),
        "odds": _odds(comp),
    }


def fetch_scoreboard(league_slug):
    """Live + upcoming matches for a league slug (eng.1, esp.1, ...).

    Merges ESPN's default window with an explicit today-date query —
    the default window lags on matchdays (esp.1 still serving yesterday's
    FTs while today's fixtures only exist under ?dates=YYYYMMDD).
    """
    from datetime import datetime, timezone
    data = _get(f"{BASE}/{league_slug}/scoreboard")
    events = list((data.get("events", []) or []) if data else [])
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    dated = _get(f"{BASE}/{league_slug}/scoreboard", params={"dates": today})
    if dated:
        events += dated.get("events", []) or []
    seen = {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        key = str(ev.get("id")) if ev.get("id") is not None else \
            f"{ev.get('date')}|{ev.get('name')}"
        seen[key] = ev
    return [m for m in (_parse_event(ev) for ev in seen.values()) if m]


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