"""Tests for engine/elo.py — ported The Open Model math."""

from engine.elo import expected_goals, match_prob, market_probs


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol


def test_expected_goals_symmetric():
    assert approx(expected_goals(1800, 1800), 1.35)


def test_expected_goals_favorite_scores_more():
    assert expected_goals(2000, 1600) > expected_goals(1600, 2000)


def test_expected_goals_clamped():
    assert expected_goals(2500, 1200) == 3.5
    assert expected_goals(1200, 2500) == 0.3


def test_match_prob_sums_to_one():
    p = match_prob(1694.8, 1630.6)  # Rayo v Espanyol Elos
    assert approx(p["home"] + p["draw"] + p["away"], 1.0, tol=1e-6)


def test_match_prob_favorite_favored():
    p = match_prob(1998, 1611.1)  # Bayern v Union Berlin Elos
    assert p["home"] > p["away"]
    assert p["home"] > 0.70


def test_match_prob_carries_xg():
    p = match_prob(1694.8, 1630.6)
    assert p["xg_home"] > p["xg_away"] > 0


def test_market_probs_dc_consistent():
    p = match_prob(1694.8, 1630.6)
    m = market_probs(1694.8, 1630.6)
    assert approx(m["dc1x"], p["home"] + p["draw"], tol=1e-6)
    assert approx(m["dcx2"], p["draw"] + p["away"], tol=1e-6)
    assert approx(m["dc12"], p["home"] + p["away"], tol=1e-6)


def test_market_probs_ordering():
    m = market_probs(1694.8, 1630.6)
    assert m["over15"] > m["over25"] > m["over35"]
    assert 0 < m["btts"] < 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
