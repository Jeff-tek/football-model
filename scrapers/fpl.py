import requests
from datetime import datetime, timezone

BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-model/1.0)"}
STATUS_MAP = {"a": "available", "d": "doubt", "i": "injured",
              "s": "suspended", "u": "unavailable", "n": "unavailable"}


def _pct(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def fetch_pl_injuries():
    r = requests.get(BOOTSTRAP, headers=HEADERS, timeout=20); r.raise_for_status()
    data = r.json()
    teams = {t["id"]: t["name"] for t in data["teams"]}
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for p in data["elements"]:
        status = STATUS_MAP.get(p["status"], "unavailable")
        if status == "available":
            continue
        chance = (p.get("chance_of_playing_this_round")
                  if p.get("chance_of_playing_this_round") is not None
                  else p.get("chance_of_playing_next_round"))
        out.append({"league": "Premier League", "team": teams.get(p["team"], "Unknown"),
                    "player": f'{p["first_name"]} {p["second_name"]}'.strip(),
                    "status": status, "chance_of_playing": _pct(chance),
                    "source": "fpl", "scraped_at": now})
    return out
