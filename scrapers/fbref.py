import io, time, random, requests, pandas as pd
from datetime import datetime, timezone
from bs4 import BeautifulSoup

LEAGUES = {"Premier League": (9, "Premier-League"), "La Liga": (12, "La-Liga"),
           "Serie A": (11, "Serie-A"), "Bundesliga": (20, "Bundesliga"),
           "Ligue 1": (13, "Ligue-1"),
           "Russian Premier League": (30, "Russian-Premier-League")}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-model/1.0)"}
MIN_DELAY, MAX_DELAY = 6, 10
_last = 0.0


def _num(v):
    try:
        s = str(v)
        return float(v) if v is not None and s not in ("nan", "") else None
    except (ValueError, TypeError):
        return None


def _int(v):
    n = _num(v); return int(n) if n is not None else None


def _get(url):
    global _last
    wait = random.uniform(MIN_DELAY, MAX_DELAY) - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(3):
        r = requests.get(url, headers=HEADERS, timeout=30)
        _last = time.time()
        if r.status_code == 429:
            time.sleep(60 * (attempt + 1)); continue
        r.raise_for_status(); return r.text
    raise RuntimeError(f"RATE LIMITED repeatedly on {url}")


def _read_tables(html):
    return pd.read_html(io.StringIO(html.replace("<!--", "").replace("-->", "")))


def fetch_standings(league, season):
    comp_id, slug = LEAGUES[league]
    url = f"https://fbref.com/en/comps/{comp_id}/{season}/{season}-{slug}-Stats"
    html = _get(url)
    soup = BeautifulSoup(html.replace("<!--", "").replace("-->", ""), "lxml")
    team_ids = {}
    for a in soup.select("a[href*='/squads/']"):
        parts = a["href"].split("/squads/")
        if len(parts) > 1:
            team_ids[a.get_text(strip=True)] = parts[1].split("/")[0]
    table = next(t for t in _read_tables(html) if "Squad" in t.columns)
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for _, r in table.iterrows():
        team = str(r["Squad"]).strip(); played = _num(r.get("MP"))
        out.append({"league": league, "season": season, "team": team,
                    "team_id": team_ids.get(team), "rank": _int(r.get("Rk")),
                    "matches_played": _int(played), "xg_for": _num(r.get("xG")),
                    "xg_against": _num(r.get("xGA")),
                    "xga_per_game": (_num(r.get("xGA")) / played) if played else None,
                    "points": _int(r.get("Pts")), "scraped_at": now})
    return out


def league_distribution(standings, field):
    vals = [r[field] for r in standings if r.get(field) is not None]
    if len(vals) < 2:
        return {"mean": None, "std": None, "n": len(vals)}
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return {"mean": mean, "std": var ** 0.5, "n": len(vals)}
