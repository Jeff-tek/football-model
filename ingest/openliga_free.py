"""Free OpenLigaDB ingest — pure fetch+parse, stdlib+requests only.

Endpoint: api.openligadb.de/getmatchdata/{shortcut}  (bl1, bl2, ...)
"""
import logging
import requests

BASE = "https://api.openligadb.de"
TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (football-model/1.0)"}
log = logging.getLogger(__name__)


def _get(url):
    """GET JSON; log + return None on any failure (never raise)."""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("openligadb fetch failed %s: %s", url, e)
        return None


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _parse_match(m):
    t1 = m.get("Team1", {}) or {}
    t2 = m.get("Team2", {}) or {}
    score = None
    for res in m.get("MatchResults", []) or []:
        r = res.get("Result", {}) or {}
        if r.get("ResultTypeID") == 2:  # final score
            score = (_to_int(r.get("PointsTeam1")), _to_int(r.get("PointsTeam2")))
            break
    if score is None and m.get("MatchResults"):
        r = (m["MatchResults"][0].get("Result", {}) or {})
        score = (_to_int(r.get("PointsTeam1")), _to_int(r.get("PointsTeam2")))
    group = m.get("Group", {}) or {}
    return {
        "id": str(m.get("MatchID", "")),
        "date": m.get("MatchDateTime", ""),
        "home": t1.get("TeamName", ""),
        "away": t2.get("TeamName", ""),
        "home_id": str(t1.get("TeamId", "")),
        "away_id": str(t2.get("TeamId", "")),
        "home_score": score[0] if score else None,
        "away_score": score[1] if score else None,
        "played": bool(m.get("MatchIsFinished", False)),
        "league": group.get("GroupName", ""),
    }


def fetch_matches(shortcut):
    """All matches for a league shortcut (bl1, bl2, ...)."""
    data = _get(f"{BASE}/getmatchdata/{shortcut}")
    if not data:
        return []
    return [_parse_match(m) for m in data if isinstance(m, dict)]