"""Grounded soccer tips: Poisson + Dixon-Coles low-score correction.

Pure functions — no I/O, no deps beyond stdlib math.
Lambdas derived from last-5 form + standings; outputs 1X2, O/U 2.5, BTTS.
"""

import math
from typing import Dict, List, Tuple

MAX_GOALS = 8  # matrix rows/cols 0..7 (8 rows, 8 cols)


# ── Core Poisson ──────────────────────────────────────────────

def _poisson_pmf(k: int, lam: float) -> float:
    """P(k | λ) = λ^k · e^{-λ} / k!"""
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_matrix(lh: float, la: float) -> List[List[float]]:
    """8×8 joint probability matrix: P(home=i, away=j) assuming independence."""
    ph = [_poisson_pmf(k, lh) for k in range(MAX_GOALS)]
    pa = [_poisson_pmf(k, la) for k in range(MAX_GOALS)]
    return [[ph[i] * pa[j] for j in range(MAX_GOALS)] for i in range(MAX_GOALS)]


def dixon_coles_adjust(matrix: List[List[float]], lh: float, la: float,
                       rho: float = 0.02) -> List[List[float]]:
    """Apply Dixon-Coles low-score correction to cells (0,0), (1,0), (0,1), (1,1).

    Sign convention: positive ρ lifts low-scoring draws (0-0, 1-1) and
    suppresses 1-0 / 0-1 (ρ here = −ρ in the original 1997 paper, whose
    empirical fit is negative). Multiplicative τ, renormalized to Σ = 1.
    """
    m = [row[:] for row in matrix]  # deep copy
    # τ multipliers
    m[0][0] *= 1.0 + rho * lh * la   # (0,0) draw lift
    m[1][0] *= 1.0 - rho * la        # (1,0) suppress
    m[0][1] *= 1.0 - rho * lh        # (0,1) suppress
    m[1][1] *= 1.0 + rho             # (1,1) draw lift

    # Clamp negatives (rho too large for given lambdas)
    for i in range(MAX_GOALS):
        for j in range(MAX_GOALS):
            if m[i][j] < 0.0:
                m[i][j] = 0.0

    # Renormalize to preserve total mass
    total = sum(m[i][j] for i in range(MAX_GOALS) for j in range(MAX_GOALS))
    if total > 0.0:
        scale = 1.0 / total
        for i in range(MAX_GOALS):
            for j in range(MAX_GOALS):
                m[i][j] *= scale
    return m


# ── Market probabilities ─────────────────────────────────────

def prob_1x2(matrix: List[List[float]]) -> Dict[str, float]:
    """{home, draw, away} from full-time result matrix."""
    home = draw = away = 0.0
    for i in range(MAX_GOALS):
        for j in range(MAX_GOALS):
            if i > j:
                home += matrix[i][j]
            elif i == j:
                draw += matrix[i][j]
            else:
                away += matrix[i][j]
    return {"home": home, "draw": draw, "away": away}


def prob_over25(matrix: List[List[float]]) -> float:
    """P(total goals > 2.5) — i.e. P(≥3 goals)."""
    return sum(matrix[i][j] for i in range(MAX_GOALS)
               for j in range(MAX_GOALS) if i + j >= 3)


def prob_btts(matrix: List[List[float]]) -> float:
    """P(both teams score ≥ 1) = 1 - P(home=0) - P(away=0) + P(0,0)."""
    p_home0 = sum(matrix[0][j] for j in range(MAX_GOALS))
    p_away0 = sum(matrix[i][0] for i in range(MAX_GOALS))
    p_00 = matrix[0][0]
    return 1.0 - p_home0 - p_away0 + p_00


# ── Odds / edge / Kelly ──────────────────────────────────────

def fair(prob: float) -> float:
    """Fair decimal odds = 1 / prob. Raises if prob ≤ 0."""
    return 1.0 / prob


def devig(odds: Dict[str, float]) -> Dict[str, float]:
    """Remove bookmaker margin (proportional devig): fair odds per outcome."""
    implied = {k: 1.0 / v for k, v in odds.items() if v and v > 1.0}
    total = sum(implied.values())
    if total <= 0.0:
        return {}
    return {k: 1.0 / (v / total) for k, v in implied.items()}


def edge_vs_book(prob: float, odds: float) -> float:
    """Expected edge = prob × odds − 1. Positive = value."""
    return prob * odds - 1.0


def kelly_fraction(prob: float, odds: float, half: bool = True) -> float:
    """Kelly criterion fraction. half=True → cap at half-Kelly, max 2%."""
    ev = edge_vs_book(prob, odds)
    if ev <= 0:
        return 0.0
    f = ev / (odds - 1.0) if odds > 1.0 else 0.0
    if half:
        f *= 0.5
    return min(f, 0.02)


# ── Orchestrator ─────────────────────────────────────────────

KELLY_CAP = 0.02
BET_BAND = 0.70       # pick prob ≥ this → BET
MARGINAL_BAND = 0.55  # pick prob ≥ this → MARGINAL
AGREE_GAP = 0.15      # max 1X2 spread across models tolerated before downgrade
CROWD_WEIGHT = 0.12   # Polymarket sentiment vote (caller skips thin markets)


def _norm_1x2(d):
    """Normalize a 1X2 dict to sum 1; None when unusable."""
    try:
        t = d["home"] + d["draw"] + d["away"]
    except (KeyError, TypeError):
        return None
    if not t or t <= 0:
        return None
    return {k: d[k] / t for k in ("home", "draw", "away")}


def build_tip(fixture_form: Dict, market_odds: Dict,
              elo_1x2: Dict | None = None, openmodel_1x2: Dict | None = None,
              crowd_1x2: Dict | None = None,
              crowd_weight: float = CROWD_WEIGHT) -> Dict:
    """Compute safest pick from form data, bookmaker odds and optional 2nd opinions.

    fixture_form / market_odds: as before.
    elo_1x2 / openmodel_1x2: optional {home, draw, away} second opinions.
    crowd_1x2: optional Polymarket {home, draw, away} sentiment (pass None for
        thin/quiet markets). Weighted at crowd_weight (default 0.12) so late
        matchday money nudges the ensemble without overriding form.

    Method: weighted-average all available 1X2 opinions (Poisson form always votes),
    then pick the highest-probability outcome across 1X2, Double Chance,
    O/U 2.5 and BTTS. Verdict from probability bands; base models disagreeing
    (1X2 spread > AGREE_GAP, crowd excluded) downgrades one band. Confidence = pick prob %.
    Edge vs book is still reported for transparency, but no longer picks.
    """
    # Lambdas from form (clamped: λ=0 makes draw prob exactly 1 → fair() divides by zero)
    lh = max(fixture_form["home_goals_for"], 0.05)   # home expected to score
    la = max(fixture_form["away_goals_for"], 0.05)   # away expected to score
    rho = fixture_form.get("rho", 0.02)
    sample = fixture_form.get("sample", 5)

    matrix = poisson_matrix(lh, la)
    matrix = dixon_coles_adjust(matrix, lh, la, rho)

    m1x2 = prob_1x2(matrix)
    m_ou = prob_over25(matrix)
    m_btts = prob_btts(matrix)

    # Ensemble 1X2 across voting models (crowd weighted, excluded from gap)
    votes = {"poisson": m1x2}
    for name, opinion in (("elo", elo_1x2), ("openmodel", openmodel_1x2)):
        n = _norm_1x2(opinion) if opinion else None
        if n:
            votes[name] = n
    weights = {name: 1.0 for name in votes}
    cn = _norm_1x2(crowd_1x2) if crowd_1x2 else None
    if cn:
        votes["crowd"] = cn
        weights["crowd"] = crowd_weight if crowd_weight and crowd_weight > 0 else CROWD_WEIGHT
    total_w = sum(weights.values())
    ens = {k: sum(votes[n][k] * weights[n] for n in votes) / total_w
           for k in ("home", "draw", "away")}

    # Safest-pick slate
    slate = {
        "Home": ens["home"], "Draw": ens["draw"], "Away": ens["away"],
        "1X": ens["home"] + ens["draw"],
        "12": ens["home"] + ens["away"],
        "X2": ens["draw"] + ens["away"],
        "Over 2.5": m_ou, "Under 2.5": 1.0 - m_ou,
        "BTTS Yes": m_btts, "BTTS No": 1.0 - m_btts,
    }
    pick = max(slate, key=lambda k: slate[k])
    prob = slate[pick]

    # Agreement across base voting models (crowd excluded — sentiment nudges, never caps)
    base = {n: v for n, v in votes.items() if n != "crowd"}
    gap = max(max(v[k] for v in base.values()) - min(v[k] for v in base.values())
              for k in ("home", "draw", "away"))
    agree = gap <= AGREE_GAP

    # Verdict from bands, downgraded a notch on disagreement
    if prob >= BET_BAND:
        verdict = "BET"
    elif prob >= MARGINAL_BAND:
        verdict = "MARGINAL"
    else:
        verdict = "NO BET"
    if not agree and len(base) > 1:
        verdict = {"BET": "MARGINAL", "MARGINAL": "NO BET"}.get(verdict, verdict)

    confidence = round(prob * 100, 1)

    # Edge vs book (display only) on ensembled 1X2
    best_key, best_edge = None, -999.0
    for key, prob_val in ens.items():
        odds_val = market_odds.get(key)
        if odds_val is None:
            continue
        ev = edge_vs_book(prob_val, odds_val)
        if ev > best_edge:
            best_edge = ev
            best_key = key

    # Fair odds from ensembled 1X2
    fair_1x2 = {k: round(fair(v), 2) for k, v in ens.items()}
    fair_ou = {"over": round(fair(m_ou), 2), "under": round(fair(1.0 - m_ou), 2)}
    fair_btts = {"yes": round(fair(m_btts), 2), "no": round(fair(1.0 - m_btts), 2)}

    # Kelly on best 1X2 edge (display only)
    best_odds = market_odds.get(best_key) if best_key else None
    kf = kelly_fraction(ens[best_key], best_odds) if best_key and best_odds else 0.0

    # Reasons
    reasons: List[str] = []
    reasons.append(f"Last-5: {fixture_form.get('home_last5', '?')} (H) vs {fixture_form.get('away_last5', '?')} (A)")
    reasons.append(f"Poisson λ_home={lh:.2f} λ_away={la:.2f}, Dixon-Coles ρ={rho}")
    for name, v in votes.items():
        reasons.append(f"{name.capitalize()} 1X2: {v['home']:.2f}/{v['draw']:.2f}/{v['away']:.2f}")
    reasons.append(f"Safest: {pick} ({prob:.1%}) across {len(slate)} markets")
    reasons.append(f"Models {'agree' if agree else 'split'} (1X2 spread {gap:.2f})"
                   + (" — verdict capped" if not agree and len(base) > 1 else ""))
    if best_key:
        reasons.append(f"Value check: {best_key} edge {best_edge:+.2%} vs book")
    reasons.append(f"Kelly (half, cap {KELLY_CAP:.0%}): {kf:.4f}")
    if sample < 10:
        reasons.append(f"Note: {sample}-game sample — variance significant; 500+ match calibration recommended")

    return {
        "pick": pick,
        "probs": {
            "1X2": {k: round(v, 4) for k, v in ens.items()},
            "DC": {"1X": round(slate["1X"], 4), "12": round(slate["12"], 4),
                   "X2": round(slate["X2"], 4)},
            "O/U 2.5": {"over": round(m_ou, 4), "under": round(1.0 - m_ou, 4)},
            "BTTS": {"yes": round(m_btts, 4), "no": round(1.0 - m_btts, 4)},
        },
        "slate": {k: round(v, 4) for k, v in slate.items()},
        "fair_odds": {"1X2": fair_1x2, "O/U 2.5": fair_ou, "BTTS": fair_btts},
        "edge": round(best_edge, 4) if best_key else None,
        "edge_market": best_key,
        "verdict": verdict,
        "reasons": reasons,
        "confidence": confidence,
        "models": sorted(votes),
        "kelly": round(kf, 4),
    }
