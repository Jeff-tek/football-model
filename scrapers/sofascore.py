import time, requests
from datetime import datetime, timezone

BASE = "https://api.sofascore.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-model/1.0)",
           "Accept": "application/json"}
DELAY_S = 3
TOURNAMENTS = {"Premier League": 17, "La Liga": 8, "Serie A": 23,
               "Bundesliga": 35, "Ligue 1": 34, "Russian Premier League": 203}


def _get(path):
    time.sleep(DELAY_S)
    r = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=20)
    if r.status_code == 404:
        return {}
    r.raise_for_status(); return r.json()


def fetch_event_lineups(event_id):
    data = _get(f"/event/{event_id}/lineups")
    if not data:
        return {"confirmed": False, "home": [], "away": []}

    def players(side):
        return [{"name": pl.get("player", {}).get("name"),
                 "is_starter": not pl.get("substitute", True)}
                for pl in data.get(side, {}).get("players", [])]
    return {"confirmed": bool(data.get("confirmed", False)),
            "home": players("home"), "away": players("away"),
            "scraped_at": datetime.now(timezone.utc).isoformat()}


def fetch_team_injuries(team_id, team_name, league):
    data = _get(f"/team/{team_id}/players")
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for entry in data.get("players", []):
        p = entry.get("player", {})
        if not (p.get("injury") or {}):
            continue
        out.append({"league": league, "team": team_name, "player": p.get("name"),
                    "status": "injured", "chance_of_playing": None,
                    "source": "sofascore", "scraped_at": now})
    return out
