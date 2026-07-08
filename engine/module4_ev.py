import math

MIN_ODDS = {"WEAK": None, "MODERATE": 2.00, "STRONG": 1.75, "VERY STRONG": 1.50}
_ORDER = ["WEAK", "MODERATE", "STRONG", "VERY STRONG"]


def signal_tier(z):
    a = abs(z)
    if a < 0.8:
        return "WEAK"
    if a < 1.5:
        return "MODERATE"
    if a <= 2.5:
        return "STRONG"
    return "VERY STRONG"


def downgrade_tier(tier, steps=1):
    return _ORDER[max(0, _ORDER.index(tier) - steps)]


def implied_prob(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def expected_value(z, decimal_odds):
    return implied_prob(z) * decimal_odds - 1


def decision(tier, ev, decimal_odds):
    if tier == "WEAK":
        return "NO BET"
    if decimal_odds is None or decimal_odds < MIN_ODDS[tier]:
        return "NO BET"
    if ev > 0.05:
        return "BET"
    if ev >= 0:
        return "MARGINAL" if tier in ("STRONG", "VERY STRONG") else "NO BET"
    return "NO BET"


def bet_type(raw, sos):
    xgdev_z = raw.get("z_xgdev") or 0
    if xgdev_z < -1.0 and sos == "CONFIRMED":
        return "Team Over 1.5 / Win / -AH (regression to scoring imminent)"
    if xgdev_z > 1.0 and sos == "INFLATED":
        return "Opponent Win / Under 2.5 / +AH (overperformance correction due)"
    return "Match Winner (primary signal)"
