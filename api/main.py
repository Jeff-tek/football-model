import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from engine.pipeline import run_fixture
from api.hydrate import hydrate_fixture
from db import SessionLocal, Standing, Match

app = FastAPI(title="Football Model API")
app.add_middleware(CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"], allow_headers=["*"])

SEASON = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/fixtures")
def fixtures(league: str):
    with SessionLocal() as s:
        rows = (s.query(Match).filter(Match.league == league, Match.played.is_(False))
                .order_by(Match.date.asc()).limit(40).all())
        return [{"home": m.home_team, "away": m.away_team, "date": str(m.date)}
                for m in rows]


@app.get("/teams")
def teams(league: str):
    with SessionLocal() as s:
        rows = s.query(Standing).filter_by(league=league, season=SEASON).all()
        return sorted(r.team for r in rows)


@app.post("/analyze_by_name")
def analyze_by_name(payload: dict = Body(...)):
    try:
        fx = hydrate_fixture(payload["league"], SEASON, payload["home"],
                             payload["away"], payload.get("overrides"))
        for side in ("home", "away"):
            if side in payload and isinstance(payload[side], dict):
                for k in ("gk_status", "impact_sub_risk", "injuries_z"):
                    if k in payload[side]:
                        fx[side][k] = payload[side][k]
            if f"{side}_h2h" in payload:
                fx[f"{side}_h2h"] = payload[f"{side}_h2h"]
        return run_fixture(fx)
    except KeyError as e:
        raise HTTPException(422, f"missing field: {e}")
    except ValueError as e:
        raise HTTPException(404, str(e))
