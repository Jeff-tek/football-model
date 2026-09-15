"""Elo → Dixon-Coles match model (second opinion alongside Poisson form).

Faithful port of The Open Model's lib/model.ts (MIT License,
https://github.com/Hicruben/theopenmodel — Elo → expected goals →
bivariate Poisson → 1X2 + derived markets).

Kept in its own module on purpose: their Dixon-Coles ρ sign convention is
opposite engine/tips.py's — the constants must never be mixed.
"""

import math

DC_RHO = -0.13       # their low-score correction (empirical fit)
HOME_ADV = 65.0      # ClubElo-style home advantage, Elo points
GRID = 9             # scoreline cells 0..8 each side


def _tau(a, b, lh, la, rho=DC_RHO):
    if a == 0 and b == 0:
        return 1 - lh * la * rho
    if a == 0 and b == 1:
        return 1 + lh * rho
    if a == 1 and b == 0:
        return 1 + la * rho
    if a == 1 and b == 1:
        return 1 - rho
    return 1.0


def expected_goals(rating, opponent, bonus=0.0):
    """Elo gap → Poisson λ. Same shape as their international backtest."""
    return max(0.3, min(3.5, 1.35 + ((rating + bonus) - opponent) / 400))


def _pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def match_prob(elo_home, elo_away, home_adv=HOME_ADV):
    """1X2 + xG from two Elo ratings. Pure function."""
    lh = expected_goals(elo_home, elo_away, home_adv)
    la = expected_goals(elo_away, elo_home, -home_adv / 2)
    home = draw = away = 0.0
    for a in range(GRID):
        pa = _pmf(a, lh)
        for b in range(GRID):
            p = pa * _pmf(b, la) * _tau(a, b, lh, la)
            if a > b:
                home += p
            elif a < b:
                away += p
            else:
                draw += p
    total = home + draw + away
    return {"home": home / total, "draw": draw / total, "away": away / total,
            "xg_home": lh, "xg_away": la}


def market_probs(elo_home, elo_away, home_adv=HOME_ADV):
    """BTTS / O-U / Double Chance from the Elo scoreline grid. Pure function."""
    lh = expected_goals(elo_home, elo_away, home_adv)
    la = expected_goals(elo_away, elo_home, -home_adv / 2)
    p = match_prob(elo_home, elo_away, home_adv)
    btts = o15 = o25 = o35 = 0.0
    for a in range(GRID):
        pa = _pmf(a, lh)
        for b in range(GRID):
            v = pa * _pmf(b, la) * _tau(a, b, lh, la)
            if a >= 1 and b >= 1:
                btts += v
            if a + b >= 2:
                o15 += v
            if a + b >= 3:
                o25 += v
            if a + b >= 4:
                o35 += v
    return {"btts": btts, "over15": o15, "over25": o25, "over35": o35,
            "dc1x": p["home"] + p["draw"],
            "dc12": p["home"] + p["away"],
            "dcx2": p["draw"] + p["away"]}
