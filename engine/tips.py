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
EDGE_BET = 0.05
EDGE_MARGINAL = 0.0


def build_tip(fixture_form: Dict, market_odds: Dict) -> Dict:
    """Compute grounded tip from form data and bookmaker odds.

    fixture_form:
        home_goals_for: float  (last-5 avg scored at home)
        home_goals_against: float  (last-5 avg conceded at home)
        away_goals_for: float  (last-5 avg scored away)
        away_goals_against: float  (last-5 avg conceded away)
        home_last5: str  (e.g. "8-14/5" → scored-conceded/games)
        away_last5: str
        sample: int (games in window, default 5)

    market_odds:
        home: float  (decimal)
        draw: float
        away: float

    Returns dict with pick, probs, fair_odds, edge, verdict, reasons, confidence.
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

    markets = {"1X2": m1x2, "O/U 2.5": {"over": m_ou, "under": 1.0 - m_ou},
               "BTTS": {"yes": m_btts, "no": 1.0 - m_btts}}

    # Pick best 1X2 edge
    best_key, best_edge, best_fair = None, -999.0, 0.0
    for key, prob_val in m1x2.items():
        odds_val = market_odds.get(key)
        if odds_val is None:
            continue
        ev = edge_vs_book(prob_val, odds_val)
        if ev > best_edge:
            best_edge = ev
            best_key = key
            best_fair = fair(prob_val)

    # Fair odds for all markets
    fair_1x2 = {k: round(fair(v), 2) for k, v in m1x2.items()}
    fair_ou = {"over": round(fair(m_ou), 2), "under": round(fair(1.0 - m_ou), 2)}
    fair_btts = {"yes": round(fair(m_btts), 2), "no": round(fair(1.0 - m_btts), 2)}

    # Verdict
    if best_key is None:
        verdict = "NO BET"
    elif best_edge > EDGE_BET:
        verdict = "BET"
    elif best_edge >= EDGE_MARGINAL:
        verdict = "MARGINAL"
    else:
        verdict = "NO BET"

    # Confidence
    if sample < 5:
        confidence = "LOW"
    elif best_edge > 0.10:
        confidence = "HIGH"
    elif best_edge > 0.05:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Kelly
    best_odds = market_odds.get(best_key) if best_key else None
    kf = kelly_fraction(m1x2[best_key], best_odds) if best_key and best_odds else 0.0

    # Reasons
    reasons: List[str] = []
    reasons.append(f"Last-5: {fixture_form.get('home_last5', '?')} (H) vs {fixture_form.get('away_last5', '?')} (A)")
    reasons.append(f"Poisson λ_home={lh:.2f} λ_away={la:.2f}, Dixon-Coles ρ={rho}")
    if best_key:
        reasons.append(f"Best edge: {best_key} (prob={m1x2[best_key]:.4f}, book={best_odds}, edge={best_edge:+.4f})")
    reasons.append(f"Kelly (half, cap {KELLY_CAP:.0%}): {kf:.4f}")
    if sample < 10:
        reasons.append(f"Note: {sample}-game sample — variance significant; 500+ match calibration recommended")

    return {
        "pick": best_key,
        "probs": {
            "1X2": {k: round(v, 4) for k, v in m1x2.items()},
            "O/U 2.5": {"over": round(m_ou, 4), "under": round(1.0 - m_ou, 4)},
            "BTTS": {"yes": round(m_btts, 4), "no": round(1.0 - m_btts, 4)},
        },
        "fair_odds": {"1X2": fair_1x2, "O/U 2.5": fair_ou, "BTTS": fair_btts},
        "edge": round(best_edge, 4) if best_key else None,
        "verdict": verdict,
        "reasons": reasons,
        "confidence": confidence,
        "kelly": round(kf, 4),
    }
