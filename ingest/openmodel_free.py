"""The Open Model free data — predictions + Elo ratings (CC BY 4.0).

CSVs: theopenmodel.com/data/predictions.csv (pre-kickoff 1X2 + modelPick),
      theopenmodel.com/data/elo-ratings.csv (club Elo ratings).
Attribution required: "Data: The Open Model (theopenmodel.com), CC BY 4.0."

6h module cache (files update with site builds). Never raises — {} / None on
any failure so our tips never break because of this feed. Stale rows
(kickoff older than 3h, or already resulted) never vote.
"""

import csv
import io
import logging
import time
import unicodedata
from datetime import datetime, timezone

import requests

BASE = "https://theopenmodel.com/data"
TIMEOUT = 20
TTL = 6 * 3600
ATTRIBUTION = "The Open Model (theopenmodel.com)"

LEAGUE_SLUGS = {"premier-league": "Premier League", "la-liga": "La Liga",
                "serie-a": "Serie A", "bundesliga": "Bundesliga",
                "ligue-1": "Ligue 1"}

_PREFIXES = ("1. fc ", "1 fc ", "as ", "ac ", "fc ", "ssc ", "us ",
             "rc ", "ca ", "ud ", "real ", "deportivo ", "sporting ")

_cache: dict[str, tuple[float, object]] = {}
log = logging.getLogger(__name__)


def _fetch(url):
    """GET text with TTL cache; None on any failure (never raise)."""
    now = time.time()
    hit = _cache.get(url)
    if hit and now - hit[0] < TTL:
        return hit[1]
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        _cache[url] = (now, r.text)
        return r.text
    except Exception as e:
        log.warning("openmodel fetch failed %s: %s", url, e)
        return hit[1] if hit else None


def _norm(name):
    """Lowercase, de-accent, strip common club prefixes — for cross-source matching."""
    s = unicodedata.normalize("NFD", (name or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace(".", " ").replace("-", " ")
    s = " ".join(s.split())
    for p in _PREFIXES:
        if s.startswith(p):
            s = s[len(p):]
            break
    return s


def _match(name, keys):
    """Exact normalized match, else token-subset match (shorter ⊆ longer)."""
    n = _norm(name)
    if n in keys:
        return n
    nt = set(n.split())
    for k in keys:
        kt = set(k.split())
        if nt and kt and (nt <= kt or kt <= nt):
            return k
    return None


def _rows(url):
    text = _fetch(url)
    if not text:
        return []
    try:
        return [r for r in csv.DictReader(io.StringIO(text)) if r]
    except Exception:
        return []


def elo_table():
    """{norm_club: (league, club, elo)} across the 5 leagues; {} on failure."""
    out = {}
    for r in _rows(f"{BASE}/elo-ratings.csv"):
        try:
            elo = float(r["elo"])
        except (KeyError, TypeError, ValueError):
            continue
        league = LEAGUE_SLUGS.get((r.get("league") or "").strip(), "")
        club = (r.get("club") or "").strip().strip('"')
        if league and club and elo > 0:
            out[_norm(club)] = (league, club, elo)
    return out


def elo_lookup(league, home, away):
    """(elo_home, elo_away) for an ESPN fixture; None when unmatched."""
    table = elo_table()
    if not table:
        return None
    home_key = _match(home, table)
    away_key = _match(away, table)
    if not home_key or not away_key:
        return None
    h, a = table[home_key], table[away_key]
    if h[0] != league or a[0] != league:
        return None
    return h[2], a[2]


def prediction_lookup(league, home, away):
    """Pre-kickoff {pHome, pDraw, pAway, modelPick, kickoff}; None when absent/stale."""
    rows = _rows(f"{BASE}/predictions.csv")
    if not rows:
        return None
    now = datetime.now(timezone.utc)
    cands = []
    for r in rows:
        try:
            if r.get("result"):
                continue
            kickoff = datetime.fromisoformat(r["kickoff"])
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            if (now - kickoff).total_seconds() > 3 * 3600:
                continue
            if LEAGUE_SLUGS.get((r.get("league") or "").strip(), "") != league:
                continue
            cands.append((kickoff, r))
        except (KeyError, TypeError, ValueError):
            continue
    homes = {_norm(r["home"]): r for _, r in cands if r.get("home")}
    for norm_home, r in homes.items():
        if not r.get("away"):
            continue
        if _match(home, [norm_home]) and _match(away, [_norm(r["away"])]):
            try:
                return {"home": float(r["pHome"]), "draw": float(r["pDraw"]),
                        "away": float(r["pAway"]), "pick": r.get("modelPick", ""),
                        "kickoff": r.get("kickoff", "")}
            except (KeyError, TypeError, ValueError):
                continue
    return None
