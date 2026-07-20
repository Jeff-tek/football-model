from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from db import SessionLocal, Standing, Match, Odds
from engine.pipeline import run_fixture
from server.hydrate import hydrate_fixture
import os

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

@app.get("/ingest")
def ingest(league: str = "", authorization: str | None = Header(None)):
    if CRON_SECRET and authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(401, "unauthorized")
    import traceback
    try:
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
        return {"ok": True, "league": "all"}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


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
