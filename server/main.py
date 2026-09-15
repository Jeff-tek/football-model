from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from db import SessionLocal, Standing, Match, Odds
from engine.pipeline import run_fixture
from server.hydrate import hydrate_fixture
import os
import time
from threading import Lock

app = FastAPI(title="Football Model API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

SEASON = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
CRON_SECRET = os.environ.get("CRON_SECRET", "")
LEAGUE_SLUGS = {"EPL": "Premier League", "La_liga": "La Liga", "Serie_A": "Serie A",
                "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1",
                "RFPL": "Russian Premier League"}
ESPN_SLUGS = {"EPL": "eng.1", "La_liga": "esp.1", "Serie_A": "ita.1",
              "Bundesliga": "ger.1", "Ligue_1": "fra.1"}
CACHE_TTL = 120  # seconds
_cache: dict[str, tuple[float, object]] = {}
_cache_lock = Lock()


def _cached(key, producer, force=False):
    """In-memory TTL cache; producer() called on miss or expiry."""
    now = time.time()
    if not force:
        with _cache_lock:
            hit = _cache.get(key)
            if hit and now - hit[0] < CACHE_TTL:
                return hit[1]
    value = producer()
    with _cache_lock:
        _cache[key] = (time.time(), value)
    return value


def _espn_slug(league):
    """Resolve league key (EPL), display name (Premier League), or raw slug (esp.1)."""
    if league in ESPN_SLUGS:
        return ESPN_SLUGS[league]
    if "." in league:
        return league
    for key, name in LEAGUE_SLUGS.items():
        if name == league and key in ESPN_SLUGS:
            return ESPN_SLUGS[key]
    return None


def _ingest_free():
    """Free ESPN + OpenLigaDB pull; warms the /live + /form cache."""
    from ingest import espn_free, openliga_free
    out = {}
    for key, slug in ESPN_SLUGS.items():
        sb = _cached(f"live:{slug}", lambda s=slug: espn_free.fetch_scoreboard(s), force=True)
        st = _cached(f"standings:{slug}", lambda s=slug: espn_free.fetch_standings(s), force=True)
        out[key] = {"scoreboard": len(sb), "standings": len(st)}
    bl1 = _cached("openliga:bl1", lambda: openliga_free.fetch_matches("bl1"), force=True)
    out["openligadb"] = {"bl1": len(bl1)}
    return out

@app.get("/ingest")
def ingest(league: str = "", source: str = "", authorization: str | None = Header(None)):
    if CRON_SECRET and authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "unauthorized")
    import traceback
    try:
        if source == "free":
            return {"ok": True, "source": "free", "leagues": _ingest_free()}
        if league:
            slug = next((k for k, v in LEAGUE_SLUGS.items() if v == league), None)
            if not slug:
                raise HTTPException(400, f"unknown league: {league}")
            from scrapers import understat
            from db import upsert_matches, upsert_standings, upsert_team_matches, upsert_distribution
            raw = understat.fetch_league_matches(slug, os.environ.get("CURRENT_SEASON_UNDERSTAT", "2025"))
            matches = [{**m, "season": SEASON} for m in raw]
            upsert_matches(matches)
            from scrapers import understat_standings as ust
            standings = ust.build_standings(matches, league, SEASON)
            upsert_standings(standings)
            upsert_team_matches(ust.build_team_matches(matches, league, SEASON))
            for field in ("xga_per_game", "xg_for", "xg_against"):
                upsert_distribution(league, SEASON, field, ust.league_distribution(standings, field))
            from ingest.run_all import _compute_league_distributions
            dists = _compute_league_distributions(league, SEASON)
            for field in ("xgdev", "form"):
                upsert_distribution(league, SEASON, field, dists[field])
            from odds.client import store_odds_for_league
            odds_cnt = store_odds_for_league(league)
            return {"ok": True, "league": league, "teams": len(standings),
                    "matches": len(matches), "odds": odds_cnt}
        from ingest.run_all import run as run_ingest
        run_ingest()
        free = _ingest_free()
        return {"ok": True, "league": "all", "free": free}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


@app.get("/live")
def live(league: str = "EPL"):
    """Free ESPN scoreboard passthrough (read-only, 120s TTL cache)."""
    slug = _espn_slug(league)
    if not slug:
        raise HTTPException(400, f"unknown league: {league}")
    from ingest import espn_free
    return _cached(f"live:{slug}", lambda: espn_free.fetch_scoreboard(slug))


@app.get("/form")
def form(team_id: str, league: str = "eng.1"):
    """Team recent results from ESPN schedule (read-only, 120s TTL cache)."""
    if not team_id:
        raise HTTPException(400, "team_id required")
    from ingest import espn_free
    return _cached(f"form:{team_id}", lambda: espn_free.fetch_team_schedule(team_id, league))


def _poisson_pmf(k, lam):
    from math import exp, factorial
    return exp(-lam) * (lam ** k) / factorial(k)


def _poisson_1x2(hg, ag):
    p_home = p_draw = p_away = 0.0
    for i in range(7):
        for j in range(7):
            p = _poisson_pmf(i, hg) * _poisson_pmf(j, ag)
            if i > j: p_home += p
            elif i == j: p_draw += p
            else: p_away += p
    return round(p_home, 3), round(p_draw, 3), round(p_away, 3)


def _poisson_o25(hg, ag):
    return round(sum(
        _poisson_pmf(i, hg) * _poisson_pmf(j, ag)
        for i in range(7) for j in range(7) if i + j > 2
    ), 3)


def _poisson_btts(hg, ag):
    return round(sum(
        _poisson_pmf(i, hg) * _poisson_pmf(j, ag)
        for i in range(1, 7) for j in range(1, 7)
    ), 3)


def _expected_goals(home_price, draw_price, away_price):
    total_implied = 1 / home_price + 1 / draw_price + 1 / away_price
    home_fair = (1 / home_price) / total_implied
    away_fair = (1 / away_price) / total_implied
    # Maximum likelihood Poisson estimate from 1X2 probs
    home_xg = max(0.3, min(4.0, -0.5 + 2.5 * home_fair + 0.8 * (home_fair - away_fair)))
    away_xg = max(0.3, min(4.0, -0.5 + 2.5 * away_fair + 0.8 * (away_fair - home_fair)))
    return home_xg, away_xg


def _to_dec(v):
    """American moneyline → decimal (standalone mirror of ingest.espn_free)."""
    try:
        s = str(v).strip().upper()
        if s in ("EVEN", "EV"):
            return 2.0
        ml = int(s)
    except (TypeError, ValueError):
        try:
            f = float(str(v))
            return round(f, 3) if f > 1 else None
        except (TypeError, ValueError):
            return None
    if abs(ml) < 100:
        return round(float(ml), 3) if ml > 1 else None
    return round(1 + ml / 100, 3) if ml > 0 else round(1 + 100 / abs(ml), 3)


def _verdict_pick(edges, p_o25, p_btts):
    """Best pick: highest positive 1X2 edge, else highest-prob market."""
    best_market, best_edge = max(edges.items(), key=lambda kv: kv[1])
    if best_edge <= 0:
        best_market = "O2.5" if p_o25 >= 0.5 else "BTTS Yes" if p_btts >= 0.5 else "Home"
        best_edge = 0.0
    return best_market, best_edge


def _team_avg(sched, team_name):
    """Last-5 avg goals for/against + WDL string for a team from ESPN schedule."""
    played = [m for m in sched if m.get("played")][-5:]
    if not played:
        return None
    gf = ga = 0
    for m in played:
        if m.get("home") == team_name:
            gf += m.get("home_score") or 0
            ga += m.get("away_score") or 0
        else:
            gf += m.get("away_score") or 0
            ga += m.get("home_score") or 0
    n = len(played)
    return gf / n, ga / n, n


def _simple_tip(hp, dp, ap):
    """Fallback Poisson tip when engine/tips.py is unavailable."""
    total_imp = 1 / hp + 1 / dp + 1 / ap
    p_home_fair = round((1 / hp) / total_imp, 3)
    p_draw_fair = round((1 / dp) / total_imp, 3)
    p_away_fair = round((1 / ap) / total_imp, 3)
    hxg, axg = _expected_goals(hp, dp, ap)
    p_home_val, p_draw_val, p_away_val = _poisson_1x2(hxg, axg)
    p_o25 = _poisson_o25(hxg, axg)
    p_btts = _poisson_btts(hxg, axg)
    edges = {
        "Home": round(p_home_val - p_home_fair, 3),
        "Draw": round(p_draw_val - p_draw_fair, 3),
        "Away": round(p_away_val - p_away_fair, 3),
    }
    best_market, best_edge = _verdict_pick(edges, p_o25, p_btts)
    best_prob = {"Home": p_home_val, "Draw": p_draw_val, "Away": p_away_val,
                 "O2.5": p_o25, "BTTS Yes": p_btts}.get(best_market, 0.5)
    if best_edge > 0.05:
        verdict = "BET"
    elif best_edge > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO BET"
    reasons = []
    if hxg > 1.3:
        reasons.append(f"Home xG {hxg:.2f} above league average")
    if axg < 0.8:
        reasons.append(f"Away xG {axg:.2f} below league average")
    if hxg - axg > 0.4:
        reasons.append(f"Significant xG gap ({hxg - axg:.2f})")
    if best_edge > 0.05:
        reasons.append(f"Edge detected ({best_edge:+.1%})")
    if not reasons:
        reasons.append("Mixed signals — limited model edge")
    return {"probs": {"1X2": [p_home_val, p_draw_val, p_away_val],
                      "O2.5": p_o25, "BTTS": p_btts},
            "fair": {"1X2": [p_home_fair, p_draw_fair, p_away_fair]},
            "edge": {"market": best_market, "value": best_edge},
            "pick": best_market, "verdict": verdict,
            "reasons": reasons, "confidence": round(best_prob * 100, 1),
            "homeXG": hxg, "awayXG": axg}


def _engine_tip(home_name, away_name, home_id, away_id, hp, dp, ap, espn_key):
    """Compose engine/tips.build_tip with form from ESPN team schedules."""
    from ingest.espn_free import fetch_team_schedule
    from engine.tips import build_tip
    hs = _cached(f"form:{home_id}", lambda: fetch_team_schedule(home_id, espn_key))
    as_ = _cached(f"form:{away_id}", lambda: fetch_team_schedule(away_id, espn_key))
    h = _team_avg(hs, home_name)
    a = _team_avg(as_, away_name)
    if not h or not a:
        return None
    hgf, hga, hn = h
    agf, aga, an = a
    form = {"home_goals_for": hgf, "home_goals_against": hga,
            "away_goals_for": agf, "away_goals_against": aga,
            "home_last5": f"{hgf * hn:.0f}-{hga * hn:.0f}/{hn}",
            "away_last5": f"{agf * an:.0f}-{aga * an:.0f}/{an}",
            "rho": 0.02, "sample": min(hn, an)}
    tip = build_tip(form, {"home": hp, "draw": dp, "away": ap})
    p = tip["probs"]
    return {"probs": {"1X2": [p["1X2"]["home"], p["1X2"]["draw"], p["1X2"]["away"]],
                      "O2.5": p["O/U 2.5"]["over"], "BTTS": p["BTTS"]["yes"]},
            "fair": {"1X2": [1 / tip["fair_odds"]["1X2"]["home"],
                             1 / tip["fair_odds"]["1X2"]["draw"],
                             1 / tip["fair_odds"]["1X2"]["away"]]},
            "edge": {"market": tip["pick"] or "Home", "value": tip["edge"] or 0.0},
            "pick": tip["pick"] or "Home", "verdict": tip["verdict"],
            "reasons": tip["reasons"],
            "confidence": {"LOW": 40, "MEDIUM": 65, "HIGH": 85}.get(tip["confidence"], 50),
            "homeXG": hgf, "awayXG": agf}


@app.get("/tips")
def tips(league: str = "La Liga"):
    espn_key = _espn_slug(league)
    if not espn_key:
        # Valid league but no free ESPN coverage → empty result, not an error
        return {"league": league, "as_of": datetime.now(timezone.utc).isoformat(),
                "ttl": 180, "cron": "vercel.json: /api/ingest 0 6 * * *", "tips": []}

    # Defensive: try ingest/espn_free.py first (parsed format), else raw ESPN
    parsed = False
    try:
        from ingest.espn_free import fetch_scoreboard
        events = _cached(f"live:{espn_key}", lambda: fetch_scoreboard(espn_key))
        parsed = True
    except (ImportError, ModuleNotFoundError):
        import requests as _req
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{espn_key}/scoreboard"
        resp = _req.get(url, timeout=15)
        events = resp.json().get("events", [])

    tips_list = []
    for ev in events:
        if parsed:
            # ingest/espn_free format: {home, away, date, odds: {home, draw, away}, ...}
            home_name = ev.get("home", "")
            away_name = ev.get("away", "")
            match_date = ev.get("date", "")
            odds = ev.get("odds", {})
            hp = odds.get("home")
            dp = odds.get("draw")
            ap = odds.get("away")
            home_id = ev.get("home_id", "")
            away_id = ev.get("away_id", "")
            home_form = ev.get("home_form", "")
            away_form = ev.get("away_form", "")
        else:
            # Raw ESPN format: competitions[0].competitors + odds
            comps = ev.get("competitions", [{}])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            sides = {c.get("homeAway", "away"): c for c in competitors if isinstance(c, dict)}
            home_c = sides.get("home", competitors[0])
            away_c = sides.get("away", competitors[1])
            home_name = (home_c.get("team") or {}).get("displayName", "")
            away_name = (away_c.get("team") or {}).get("displayName", "")
            match_date = ev.get("date", "")
            odds_list = comp.get("odds", [])
            dk = next((o for o in odds_list if "draftkings" in (o.get("provider") or {}).get("name", "").lower()), None)
            if not dk:
                dk = odds_list[0] if odds_list else None
            if not dk:
                continue
            hp = _to_dec((dk.get("homeTeamOdds") or {}).get("moneyLine"))
            dp = _to_dec((dk.get("drawOdds") or {}).get("moneyLine"))
            ap = _to_dec((dk.get("awayTeamOdds") or {}).get("moneyLine"))
            home_id = (home_c.get("team") or {}).get("id", "")
            away_id = (away_c.get("team") or {}).get("id", "")
            home_form = home_c.get("form", "") or ""
            away_form = away_c.get("form", "") or ""

        if not all([hp, dp, ap]):
            continue
        if hp <= 1 or dp <= 1 or ap <= 1:
            continue

        # Compose engine/tips when available, else simplified Poisson
        tip = None
        try:
            tip = _engine_tip(home_name, away_name, home_id, away_id, hp, dp, ap, espn_key)
        except Exception:
            tip = None
        if not tip:
            tip = _simple_tip(hp, dp, ap)

        tips_list.append({
            "home": home_name, "away": away_name,
            "date": match_date,
            "probs": tip["probs"],
            "fair": tip["fair"],
            "edge": tip["edge"],
            "pick": tip["pick"], "verdict": tip["verdict"],
            "reasons": tip["reasons"],
            "confidence": tip["confidence"],
            "sources": [
                {"name": "ESPN", "url": f"https://www.espn.com/soccer/scoreboard/_/league/{espn_key}"},
                {"name": "OddsPortal", "url": "https://www.oddsportal.com/football/"},
                {"name": "BetExplorer", "url": "https://www.betexplorer.com/football/"},
                {"name": "ToolsGambling", "url": "https://www.toolsgambling.com/live-odds"},
                {"name": "OddsGPT", "url": "https://www.oddsgpt.com/poisson-model"},
            ],
            "homeForm": home_form, "awayForm": away_form,
            "homeXG": tip["homeXG"], "awayXG": tip["awayXG"],
            "bookOdds": {"home": hp, "draw": dp, "away": ap},
        })

    return {"league": league, "as_of": datetime.now(timezone.utc).isoformat(),
            "ttl": 180, "cron": "vercel.json: /api/ingest 0 6 * * *",
            "tips": tips_list}


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/fixtures")
def fixtures(league: str):
    with SessionLocal() as s:
        now = datetime.now(timezone.utc)
        rows = (
            s.query(Match)
            .filter(Match.league == league, Match.season == SEASON)
            .filter(Match.date >= now)
            .order_by(Match.date.asc())
            .limit(20)
            .all()
        )
        return [{"home": m.home_team, "away": m.away_team, "date": str(m.date)} for m in rows]

@app.get("/upcoming")
def upcoming(league: str = ""):
    with SessionLocal() as s:
        q = s.query(Odds)
        if league:
            q = q.filter(Odds.league == league)
        rows = q.order_by(Odds.league, Odds.home_team).limit(50).all()
        return [{"league": r.league, "home": r.home_team, "away": r.away_team,
                 "home_odds": r.home_price, "away_odds": r.away_price} for r in rows]

@app.get("/teams")
def teams(league: str):
    with SessionLocal() as s:
        rows = s.query(Standing).filter_by(league=league, season=SEASON).all()
    return sorted(r.team for r in rows)

@app.post("/analyze_by_name")
def analyze_by_name(payload: dict = Body(...)):
    try:
        fx = hydrate_fixture(payload["league"], SEASON, payload["home"], payload["away"], payload.get("overrides"))
    except ValueError as e:
        return {"stop": True, "verdict": "NO BET", "reason": str(e)}
    for side in ("home", "away"):
        gk = payload.get(f"{side}_gk")
        if gk:
            fx[side]["gk_status"] = gk
    return run_fixture(fx)
