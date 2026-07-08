import json, re, time, requests
from datetime import datetime, timezone

BASE = "https://understat.com"
LEAGUES = {"EPL": "Premier League", "La_liga": "La Liga", "Serie_A": "Serie A",
           "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1",
           "RFPL": "Russian Premier League"}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-model/1.0)"}
CRAWL_DELAY_S = 4


def _num(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _decode(html, var):
    m = re.search(var + r"\s*=\s*JSON\.parse\('([^']+)'\)", html)
    if not m:
        raise ValueError(f"STRUCTURE CHANGE: '{var}' not found")
    return json.loads(m.group(1).encode().decode("unicode_escape"))


def _get(url):
    time.sleep(CRAWL_DELAY_S)
    r = requests.get(url, headers=HEADERS, timeout=20); r.raise_for_status()
    return r.text


def fetch_league_matches(slug, season):
    data = _decode(_get(f"{BASE}/league/{slug}/{season}"), "datesData")
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for m in data:
        played = m.get("isResult", False)
        out.append({
            "understat_match_id": m["id"], "league": LEAGUES[slug], "season": season,
            "date": m["datetime"], "home_team": m["h"]["title"], "away_team": m["a"]["title"],
            "home_goals": _num(m["goals"]["h"]) if played else None,
            "away_goals": _num(m["goals"]["a"]) if played else None,
            "home_xg": _num(m["xG"]["h"]) if played else None,
            "away_xg": _num(m["xG"]["a"]) if played else None,
            "played": played, "scraped_at": now})
    return out
