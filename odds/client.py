import os, requests

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
    for ev in fetch_h2h_odds(league):
        if ev["home_team"] == home_team and ev["away_team"] == away_team:
            p = ev["prices"]
            return {"home": p.get(home_team), "away": p.get(away_team)}
    return {}
