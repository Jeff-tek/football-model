import requests
from datetime import datetime, timezone

BASE = "https://understat.com"
LEAGUES = {"EPL": "Premier League", "La_liga": "La Liga", "Serie_A": "Serie A",
           "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1",
           "RFPL": "Russian Premier League"}
# AJAX headers: Understat now serves match data via XHR, not embedded HTML.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; football-model/1.0)",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": BASE + "/",
}


def _num(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _get_league_data(slug, season):
    """Understat's post-2025 AJAX endpoint. Returns parsed JSON."""
    url = f"{BASE}/getLeagueData/{slug}/{season}"
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        raise ValueError(
            f"STRUCTURE CHANGE: getLeagueData for {slug}/{season} "
            f"did not return JSON. First 200 chars: {r.text[:200]!r}")


def _iter_matches(payload):
    """Normalize the endpoint's shape into a flat list of match dicts.
    Understat returns either a list of matches or a dict wrapping one
    (commonly under 'datesData' / 'dates' / 'matches'); handle both."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("datesData", "dates", "matches", "data"):
            if isinstance(payload.get(key), list):
                return payload[key]
        # last resort: first list-valued field
        for v in payload.values():
            if isinstance(v, list):
                return v
    raise ValueError(f"STRUCTURE CHANGE: unrecognized payload keys: "
                     f"{list(payload)[:10] if isinstance(payload, dict) else type(payload)}")


def fetch_league_matches(slug, season):
    data = _iter_matches(_get_league_data(slug, season))
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for m in data:
        played = m.get("isResult", False)
        out.append({
            "understat_match_id": str(m.get("id")),
            "league": LEAGUES[slug], "season": season,
            "date": m.get("datetime"),
            "home_team": (m.get("h") or {}).get("title"),
            "away_team": (m.get("a") or {}).get("title"),
            "home_goals": _num((m.get("goals") or {}).get("h")) if played else None,
            "away_goals": _num((m.get("goals") or {}).get("a")) if played else None,
            "home_xg": _num((m.get("xG") or {}).get("h")) if played else None,
            "away_xg": _num((m.get("xG") or {}).get("a")) if played else None,
            "played": played, "scraped_at": now,
        })
    return out
