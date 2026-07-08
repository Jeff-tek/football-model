from db import SessionLocal, Match


def derive_h2h(home_team, away_team, limit=5):
    with SessionLocal() as s:
        rows = (s.query(Match)
                .filter(Match.played.is_(True))
                .filter(((Match.home_team == home_team) & (Match.away_team == away_team)) |
                        ((Match.home_team == away_team) & (Match.away_team == home_team)))
                .order_by(Match.date.desc()).limit(limit).all())
    return [{"home_team": m.home_team, "away_team": m.away_team, "date": str(m.date),
             "home_goals": int(m.home_goals), "away_goals": int(m.away_goals),
             "venue": None, "competition": "League"} for m in rows]
