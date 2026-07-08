RECENCY = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.5, 0.5, 0.5, 0.5]
GK_DELTA = {"first_choice_top5": 0.0, "first_choice_avg": -0.05,
            "backup": -0.15, "emergency": -0.25}
_PTS = {"W": 1, "D": 0, "L": -1}


def _weighted(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    w = RECENCY[:len(vals)]
    return sum(v * wi for v, wi in zip(vals, w)) / sum(w)


def weighted_xg_deviation(matches):
    return _weighted([m["goals"] - m["xg_for"] for m in matches])


def weighted_form(matches):
    return _weighted([_PTS[m["result"]] for m in matches])


def avg_ppda(matches):
    vals = [m["ppda"] for m in matches if m.get("ppda") is not None]
    return sum(vals) / len(vals) if vals else None


def oss(opp_form_points, opp_xga_trend, league_avg_xga):
    return (opp_form_points / 15) * 0.5 + (1 - opp_xga_trend / league_avg_xga) * 0.5


def sos_flag(matches, league_avg_xga):
    strong = weak = 0
    for m in matches:
        o = oss(m["opp_form_points"], m["opp_xga_trend"], league_avg_xga)
        if o >= 0.70:
            strong += 1
        elif o < 0.40:
            weak += 1
    n = len(matches) or 1
    if strong / n >= 0.6:
        return "CONFIRMED"
    if weak / n >= 0.6:
        return "INFLATED"
    return "NEUTRAL"


def sos_multiplier(flag):
    return {"CONFIRMED": 1.15, "INFLATED": 0.80}.get(flag, 1.0)


def zscore(value, dist):
    if value is None or not dist or not dist.get("std"):
        return None
    return (value - dist["mean"]) / dist["std"]


def metric_set(matches, dists, league_avg_xga, sos_adjust=True):
    if not matches:
        return {"z_xgdev": None, "z_form": None, "z_ppda": None,
                "sos": "NEUTRAL", "raw": {}}
    xgdev = weighted_xg_deviation(matches)
    form = weighted_form(matches)
    ppda = avg_ppda(matches)
    flag = sos_flag(matches, league_avg_xga)
    if sos_adjust:
        mult = sos_multiplier(flag)
        xgdev = xgdev * mult if xgdev is not None else None
        form = form * mult if form is not None else None
    return {"z_xgdev": zscore(xgdev, dists["xgdev"]),
            "z_form": zscore(form, dists["form"]),
            "z_ppda": zscore(ppda, dists["ppda"]),
            "sos": flag, "raw": {"xgdev": xgdev, "form": form, "ppda": ppda}}
