def _gd(meeting, home_team):
    if meeting["home_team"] == home_team:
        return meeting["home_goals"] - meeting["away_goals"]
    return meeting["away_goals"] - meeting["home_goals"]


def h2h_classify(meetings, home_team, venue_wins, venue_gd):
    if not meetings:
        return {"signal": "NEUTRAL", "recency_override": False}
    signal = "ADVANTAGE" if (venue_wins >= 0.6 and venue_gd > 0.5) else "NEUTRAL"
    last3 = meetings[:3]
    full_trend = sum(1 for m in meetings if _gd(m, home_team) > 0)
    last3_trend = sum(1 for m in last3 if _gd(m, home_team) > 0)
    recency_override = (len(meetings) >= 4 and
                        (last3_trend >= 2) != (full_trend > len(meetings) / 2))
    return {"signal": signal, "recency_override": recency_override}
