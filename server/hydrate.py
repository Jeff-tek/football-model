from datetime import datetime, timezone
from db import (SessionLocal, Standing, TeamMatch, Injury, Manager,
                get_distribution, opponent_form_as_of)
from odds.client import odds_for_fixture
from engine.module1_gather import h2h_classify
from scrapers.h2h_managers import derive_h2h


def _team_id(session, league, season, team_name):
    row = (session.query(Standing)
           .filter_by(league=league, season=season, team=team_name).one_or_none())
    return (row.team_id, row) if row else (None, None)


def _opp_form_points(form_str):
    if not form_str:
        return 7
    return sum({"W": 3, "D": 1, "L": 0}.get(c, 0) for c in form_str[:5])


def _matches_for(session, team_id, season, limit=10):
    rows = (session.query(TeamMatch)
            .filter(TeamMatch.team_id == team_id, TeamMatch.season == season)
            .order_by(TeamMatch.date.desc()).limit(limit).all())
    out = []
    for m in rows:
        opp = (session.query(Standing)
               .filter_by(season=season, team=m.opponent).one_or_none())
        ctx = {"form": None, "xga_trend": None}
        if opp and opp.team_id:
            ctx = opponent_form_as_of(opp.team_id, m.date, last_n=5)
        out.append({"venue": m.venue,
                    "goals": float(m.gf) if m.gf is not None else 0.0,
                    "xg_for": m.xg_for,  # keep None if missing — engine handles it
                    "result": (m.result or "D")[:1], "ppda": m.ppda,
                    "opp_form_points": _opp_form_points(ctx["form"]),
                    "opp_xga_trend": ctx["xga_trend"] or 1.4})
    return out


def _injuries_z(session, league, team_name):
    n = (session.query(Injury).filter_by(league=league, team=team_name)
         .filter(Injury.status.in_(["injured", "suspended", "doubt"])).count())
    return round(-0.1 * min(n, 4), 2)


def _weeks_in_post(session, team_name):
    mgr = (session.query(Manager).filter_by(team=team_name)
           .order_by(Manager.scraped_at.desc()).first())
    if not mgr or not mgr.appointed_on:
        return 99, False
    try:
        appointed = datetime.fromisoformat(mgr.appointed_on[:10])
        if appointed.tzinfo is None:
            appointed = appointed.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - appointed).days // 7, bool(mgr.is_caretaker)
    except ValueError:
        return 99, bool(mgr.is_caretaker)


def _league_avg_xga(session, league, season):
    d = get_distribution(league, season, "xga_per_game")
    return d["mean"] if d and d["mean"] else 1.4


def _ppda_dist(session, season):
    vals = [m.ppda for m in session.query(TeamMatch)
            .filter(TeamMatch.season == season, TeamMatch.ppda.isnot(None)).all()]
    if len(vals) < 2:
        return {"mean": 10.0, "std": 2.0}
    mean = sum(vals) / len(vals)
    std = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
    return {"mean": mean, "std": std or 2.0}


def hydrate_fixture(league, season, home_name, away_name, meta_overrides=None):
    with SessionLocal() as s:
        home_id, home_row = _team_id(s, league, season, home_name)
        away_id, away_row = _team_id(s, league, season, away_name)
        if not home_id or not away_id:
            raise ValueError(f"team not found: {home_name if not home_id else away_name}")

        def team(name, tid):
            weeks, care = _weeks_in_post(s, name)
            return {"name": name, "matches": _matches_for(s, tid, season),
                    "gk_status": "first_choice_avg", "injuries_z": _injuries_z(s, league, name),
                    "manager_weeks": weeks, "is_caretaker": care, "impact_sub_risk": False}

        home = team(home_name, home_id)
        away = team(away_name, away_id)
        sample = min(len(home["matches"]), len(away["matches"]))
        def _read_dist(field, fallback):
            d = get_distribution(league, season, field)
            return {"mean": d["mean"], "std": d["std"]} if d and d["mean"] is not None else fallback
        dists = {"xgdev": _read_dist("xgdev", {"mean": 0.0, "std": 0.5}),
                 "form": _read_dist("form", {"mean": 0.0, "std": 0.5}),
                 "ppda": _ppda_dist(s, season)}
        league_avg = _league_avg_xga(s, league, season)
        odds = odds_for_fixture(league, home_name, away_name)

    meetings = derive_h2h(home_name, away_name)
    home_m = [m for m in meetings if m["home_team"] == home_name]
    away_m = [m for m in meetings if m["home_team"] == away_name]
    def _venue_stats(mlist):
        n = len(mlist)
        if n == 0:
            return 0.0, 0.0
        wins = sum(1 for m in mlist if m["home_goals"] > m["away_goals"])
        gd = sum(m["home_goals"] - m["away_goals"] for m in mlist)
        return wins / n, gd / n
    vw_h, vgd_h = _venue_stats(home_m)
    vw_a, vgd_a = _venue_stats(away_m)
    home_h2h = h2h_classify(meetings, home_name, vw_h, vgd_h)
    away_h2h = h2h_classify(meetings, away_name, vw_a, vgd_a)

    meta = {"league": league, "season": season,
            "matchweek": home_row.matches_played or 0, "sample": sample,
            "league_avg_xga": league_avg, "neutral": False, "rivalry": False}
    if meta_overrides:
        meta.update(meta_overrides)
    return {"meta": meta, "dists": dists, "odds": odds,
            "home_h2h": home_h2h["signal"], "away_h2h": away_h2h["signal"],
            "home": home, "away": away}
