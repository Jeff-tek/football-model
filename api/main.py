from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from db import SessionLocal, Standing, Match
from engine.pipeline import run_fixture
from api.hydrate import hydrate_fixture
import os

app = FastAPI(title="Football Model API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

SEASON = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/fixtures")
def fixtures(league: str, days: int = 7):
    with SessionLocal() as s:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (
            s.query(Match)
            .filter(Match.league == league, Match.date >= cutoff)
            .order_by(Match.date.asc())
            .limit(40)
            .all()
        )
        return [{"home": m.home_team, "away": m.away_team, "date": str(m.date)} for m in rows]

@app.get("/teams")
def teams(league: str):
    with SessionLocal() as s:
        rows = s.query(Standing).filter_by(league=league, season=SEASON).all()
    return sorted(r.team for r in rows)

@app.post("/analyze_by_name")
def analyze_by_name(payload: dict = Body(...)):
    fx = hydrate_fixture(payload["league"], SEASON, payload["home"], payload["away"], payload.get("overrides"))
    return run_fixture(fx)
