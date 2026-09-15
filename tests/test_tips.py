"""Tests for engine/tips.py — Poisson + Dixon-Coles grounded tips."""

from engine.tips import (
    poisson_matrix, dixon_coles_adjust, prob_1x2, prob_over25,
    prob_btts, fair, devig, edge_vs_book, kelly_fraction, build_tip,
)


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol


# ── Poisson matrix ───────────────────────────────────────────

def test_poisson_matrix_sums_to_one():
    m = poisson_matrix(1.6, 1.2)
    total = sum(m[i][j] for i in range(8) for j in range(8))
    assert approx(total, 1.0)


def test_poisson_matrix_00_cell():
    m = poisson_matrix(1.6, 1.2)
    assert approx(m[0][0], 0.0608, tol=0.001)


def test_poisson_matrix_10_cell():
    m = poisson_matrix(1.6, 1.2)
    assert approx(m[1][0], 0.0973, tol=0.001)


def test_poisson_independence():
    """P(i,j) = P_home(i) * P_away(j)."""
    m = poisson_matrix(1.6, 1.2)
    import math
    ph1 = math.exp(-1.6) * 1.6 ** 1 / math.factorial(1)
    pa2 = math.exp(-1.2) * 1.2 ** 2 / math.factorial(2)
    assert approx(m[1][2], ph1 * pa2)


# ── Dixon-Coles ──────────────────────────────────────────────

def test_dixon_coles_draw_lift():
    """ρ > 0 should increase draw probability vs raw Poisson."""
    m_raw = poisson_matrix(1.6, 1.2)
    m_adj = dixon_coles_adjust(m_raw, 1.6, 1.2, rho=0.02)
    draw_raw = sum(m_raw[i][i] for i in range(8))
    draw_adj = sum(m_adj[i][i] for i in range(8))
    assert draw_adj > draw_raw, "ρ > 0 should lift draws"


def test_dixon_coles_preserves_mass():
    m = poisson_matrix(1.6, 1.2)
    m_adj = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    total = sum(m_adj[i][j] for i in range(8) for j in range(8))
    assert approx(total, 1.0)


def test_dixon_coles_00_increases():
    """Draw-lift convention: positive ρ raises the 0-0 cell."""
    m = poisson_matrix(1.6, 1.2)
    m_adj = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    assert m_adj[0][0] > m[0][0]


def test_dixon_coles_10_decreases():
    """Draw-lift convention: positive ρ suppresses the 1-0 cell."""
    m = poisson_matrix(1.6, 1.2)
    m_adj = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    assert m_adj[1][0] < m[1][0]


# ── Market probs ─────────────────────────────────────────────

def test_prob_1x2_sums_to_one():
    m = poisson_matrix(1.6, 1.2)
    m = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    p = prob_1x2(m)
    assert approx(p["home"] + p["draw"] + p["away"], 1.0)


def test_prob_1x2_values():
    m = poisson_matrix(1.6, 1.2)
    m = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    p = prob_1x2(m)
    assert approx(p["home"], 0.4641, tol=0.005)
    assert approx(p["draw"], 0.2519, tol=0.005)
    assert approx(p["away"], 0.2840, tol=0.005)


def test_prob_over25():
    m = poisson_matrix(1.6, 1.2)
    m = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    assert approx(prob_over25(m), 0.5304, tol=0.005)


def test_prob_btts():
    m = poisson_matrix(1.6, 1.2)
    m = dixon_coles_adjust(m, 1.6, 1.2, rho=0.02)
    assert approx(prob_btts(m), 0.5600, tol=0.005)


def test_btts_symmetric():
    """BTTS(λh, λa) == BTTS(λa, λh)."""
    m1 = dixon_coles_adjust(poisson_matrix(1.6, 1.2), 1.6, 1.2)
    m2 = dixon_coles_adjust(poisson_matrix(1.2, 1.6), 1.2, 1.6)
    assert approx(prob_btts(m1), prob_btts(m2))


# ── Odds / edge / Kelly ──────────────────────────────────────

def test_fair_odds():
    assert approx(fair(0.4), 2.5)
    assert approx(fair(0.5), 2.0)


def test_devig_removes_margin():
    """Book odds with overround → devigged odds imply probs summing to 1."""
    d = devig({"home": 2.30, "draw": 3.40, "away": 3.10})
    implied = sum(1.0 / v for v in d.values())
    assert approx(implied, 1.0)
    assert d["home"] > 2.30, "fair odds should be higher than book odds"


def test_edge_positive():
    assert approx(edge_vs_book(0.5, 2.5), 0.25)


def test_edge_negative():
    assert approx(edge_vs_book(0.3, 3.0), -0.1)


def test_kelly_zero_when_negative_edge():
    assert kelly_fraction(0.3, 3.0) == 0.0


def test_kelly_positive_and_capped():
    k = kelly_fraction(0.5, 2.5)
    assert k > 0
    assert k <= 0.02, "half-Kelly capped at 2%"


def test_kelly_at_cap():
    """Very high edge should hit the 2% cap."""
    k = kelly_fraction(0.8, 2.0)
    assert k == 0.02


# ── build_tip end-to-end ─────────────────────────────────────

def _rayo_espanyol_form():
    """Rayo 8-14/5 (H), Espanyol 8-5/5 (A) — last-5 records."""
    return {
        "home_goals_for": 1.6,      # 8/5
        "home_goals_against": 2.8,  # 14/5
        "away_goals_for": 1.6,      # 8/5
        "away_goals_against": 1.0,  # 5/5
        "home_last5": "8-14/5",
        "away_last5": "8-5/5",
        "rho": 0.02,
        "sample": 5,
    }


def test_build_tip_returns_all_keys():
    tip = build_tip(_rayo_espanyol_form(), {"home": 2.30, "draw": 3.40, "away": 3.10})
    assert "pick" in tip
    assert "probs" in tip
    assert "fair_odds" in tip
    assert "edge" in tip
    assert "verdict" in tip
    assert "reasons" in tip
    assert "confidence" in tip


def test_build_tip_probs_rounded():
    tip = build_tip(_rayo_espanyol_form(), {"home": 2.30, "draw": 3.40, "away": 3.10})
    assert 0 < tip["probs"]["1X2"]["home"] < 1
    assert 0 < tip["probs"]["O/U 2.5"]["over"] < 1
    assert 0 < tip["probs"]["BTTS"]["yes"] < 1


def test_build_tip_verdict_valid():
    tip = build_tip(_rayo_espanyol_form(), {"home": 2.30, "draw": 3.40, "away": 3.10})
    assert tip["verdict"] in ("BET", "MARGINAL", "NO BET")


def test_build_tip_reasons_nonempty():
    tip = build_tip(_rayo_espanyol_form(), {"home": 2.30, "draw": 3.40, "away": 3.10})
    assert len(tip["reasons"]) >= 3


def test_build_tip_mentions_form():
    tip = build_tip(_rayo_espanyol_form(), {"home": 2.30, "draw": 3.40, "away": 3.10})
    form_reason = tip["reasons"][0]
    assert "8-14/5" in form_reason and "8-5/5" in form_reason


def test_build_tip_confidence_low_sample():
    form = _rayo_espanyol_form()
    form["sample"] = 3
    tip = build_tip(form, {"home": 2.30, "draw": 3.40, "away": 3.10})
    assert tip["confidence"] == "LOW"
    assert any("variance" in r.lower() for r in tip["reasons"])


def test_build_tip_no_odds_all_no_bet():
    tip = build_tip(_rayo_espanyol_form(), {})
    assert tip["verdict"] == "NO BET"
    assert tip["pick"] is None


def test_build_tip_extreme_edge_is_bet():
    """Artificially low odds to guarantee BET."""
    tip = build_tip(_rayo_espanyol_form(), {"home": 1.01, "draw": 50.0, "away": 50.0})
    assert tip["verdict"] == "BET"


def test_build_tip_kelly_in_output():
    tip = build_tip(_rayo_espanyol_form(), {"home": 2.30, "draw": 3.40, "away": 3.10})
    assert 0.0 <= tip["kelly"] <= 0.02


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
