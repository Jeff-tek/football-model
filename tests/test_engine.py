from engine.preflight import season_phase_gate, manager_gate
from engine.module2_metrics import (sos_flag, zscore, weighted_xg_deviation,
                                    weighted_form)
from engine.module3_composite import composite, apply_modifiers
from engine.module4_ev import (signal_tier, implied_prob, expected_value,
                               decision, downgrade_tier)
from engine.pipeline import run_fixture


def approx(a, b, tol=1e-4):
    return abs(a - b) <= tol


def test_season_phase():
    assert season_phase_gate(15, 4)["proceed"] is False
    g = season_phase_gate(15, 7)
    assert g["proceed"] and g["phase"] == "Mid"
    assert "REDUCED SAMPLE — LOWER CONFIDENCE" in g["flags"]


def test_manager_gate():
    assert manager_gate(99, False)["discard_ppda"] is False
    assert manager_gate(3, False)["discard_ppda"] is True
    assert manager_gate(99, True)["downgrade"] is True


def test_sos():
    strong = [{"opp_form_points": 15, "opp_xga_trend": 0.7} for _ in range(10)]
    weak = [{"opp_form_points": 0, "opp_xga_trend": 2.1} for _ in range(10)]
    assert sos_flag(strong, 1.4) == "CONFIRMED"
    assert sos_flag(weak, 1.4) == "INFLATED"


def test_weighted_metrics():
    m = [{"goals": 3, "xg_for": 1.5, "result": "W"} for _ in range(5)]
    assert approx(weighted_xg_deviation(m), 1.5)
    assert approx(weighted_form(m), 1.0)


def test_zscore():
    assert approx(zscore(2.0, {"mean": 0.0, "std": 0.5}), 4.0)
    assert zscore(1.0, {"mean": 0, "std": 0}) is None


def test_composite():
    assert approx(composite(1.0, 1.0, 1.0, 0, 0, include_ppda=True), 0.85)
    assert approx(composite(1.0, 1.0, 1.0, 0, 0, include_ppda=False), 0.5 / 0.65)


def test_modifiers():
    assert approx(apply_modifiers(1.0, "ADVANTAGE")["z"], 1.05)
    capped = apply_modifiers(3.0, "NEUTRAL", rivalry=True)
    assert capped["rivalry_capped"] and approx(capped["z"], 1.5)


def test_tiers_and_ev():
    assert signal_tier(0.5) == "WEAK"
    assert signal_tier(2.0) == "STRONG"
    assert approx(implied_prob(0.0), 0.5)
    assert approx(expected_value(0.0, 2.0), 0.0)
    assert downgrade_tier("STRONG") == "MODERATE"


def test_decision_gates():
    assert decision("WEAK", 0.5, 3.0) == "NO BET"
    assert decision("MODERATE", 0.2, 1.9) == "NO BET"
    assert decision("MODERATE", 0.2, 2.1) == "BET"
    assert decision("STRONG", 0.02, 1.8) == "MARGINAL"


def _team(name, hd, ad, hr, ar, hp, ap, fp, xga, gk, inj=0.0):
    def mk(v, d, r, p):
        return [{"venue": v, "goals": 1.5 + d, "xg_for": 1.5, "result": r,
                 "ppda": p, "opp_form_points": fp, "opp_xga_trend": xga}
                for _ in range(5)]
    return {"name": name, "gk_status": gk, "injuries_z": inj,
            "matches": mk("H", hd, hr, hp) + mk("A", ad, ar, ap)}


def build_fixture():
    alpha = _team("Alpha", 1.5, 0.5, "W", "W", 7, 9, 15, 0.7, "first_choice_top5")
    beta = _team("Beta", -1.5, -1.2, "L", "L", 13, 14, 0, 2.1, "backup", inj=-0.3)
    dists = {"xgdev": {"mean": 0.0, "std": 0.5}, "form": {"mean": 0.0, "std": 0.5},
             "ppda": {"mean": 10.0, "std": 2.0}}
    return {"home": alpha, "away": beta, "dists": dists,
            "odds": {"home": 2.10, "away": 3.50},
            "meta": {"league": "Premier League", "matchweek": 20, "sample": 10,
                     "league_avg_xga": 1.4, "neutral": False, "rivalry": False}}


def test_full_pipeline():
    r = run_fixture(build_fixture())
    assert r["pick"] == "home" and r["pickTeam"] == "Alpha"
    assert r["verdict"] == "BET" and r["ev"] > 0
    return r


def test_insufficient_sample_stops():
    fx = build_fixture(); fx["meta"]["sample"] = 3
    assert run_fixture(fx)["verdict"] == "NO BET"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t(); print(f"PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
