from engine.preflight import season_phase_gate, manager_gate
from engine.module2_metrics import metric_set, GK_DELTA
from engine.module3_composite import venue_blend, composite, apply_modifiers
from engine.module4_ev import (signal_tier, downgrade_tier, expected_value,
                               decision, bet_type)


def analyze_team(team, dists, league_avg_xga, is_home, neutral, ppda_valid):
    home = [m for m in team["matches"] if m["venue"] == "H"]
    away = [m for m in team["matches"] if m["venue"] == "A"]
    hm = metric_set(home, dists, league_avg_xga)
    am = metric_set(away, dists, league_avg_xga)
    z_xgdev = venue_blend(hm["z_xgdev"], am["z_xgdev"], is_home, neutral)
    z_form = venue_blend(hm["z_form"], am["z_form"], is_home, neutral)
    z_ppda = venue_blend(hm["z_ppda"], am["z_ppda"], is_home, neutral)
    gk = GK_DELTA.get(team.get("gk_status", "first_choice_avg"), -0.05)
    z_inj = team.get("injuries_z", 0.0)
    z_raw = composite(z_xgdev, z_form, z_ppda, z_inj, gk, include_ppda=ppda_valid)
    dom = hm if is_home else am
    return {"z_pre_mod": z_raw, "sos": dom["sos"], "raw": dom["raw"],
            "z_ppda_used": ppda_valid, "gk_delta": gk,
            "components": {"z_xgdev": z_xgdev, "z_form": z_form, "z_ppda": z_ppda}}


def run_fixture(fixture):
    meta = fixture["meta"]
    gate = season_phase_gate(meta["matchweek"], meta["sample"])
    if not gate["proceed"]:
        return {"stop": True, "verdict": "NO BET", "reason": gate["msg"], "meta": meta,
                "fx": {"home": fixture["home"], "away": fixture["away"]}}
    results = {}
    for side in ("home", "away"):
        team = fixture[side]
        mg = manager_gate(team.get("manager_weeks", 99), team.get("is_caretaker", False))
        a = analyze_team(team, fixture["dists"], meta["league_avg_xga"],
                         is_home=(side == "home"), neutral=meta.get("neutral", False),
                         ppda_valid=not mg["discard_ppda"])
        mod = apply_modifiers(a["z_pre_mod"], fixture.get(f"{side}_h2h", "NEUTRAL"),
                              meta.get("rivalry", False))
        tier = signal_tier(mod["z"])
        if team.get("impact_sub_risk") or mg["downgrade"]:
            tier = downgrade_tier(tier)
        results[side] = {**a, "z_final": mod["z"], "tier": tier,
                         "manager": mg["status"], "rivalry_capped": mod["rivalry_capped"]}
    pick = max(results, key=lambda s: results[s]["z_final"])
    r = results[pick]
    odds = fixture["odds"].get(pick)
    ev = expected_value(r["z_final"], odds) if odds else None
    verdict = decision(r["tier"], ev, odds) if ev is not None else "MONITOR"
    return {"stop": False, "pick": pick, "pickTeam": fixture[pick]["name"],
            "z_home": round(results["home"]["z_final"], 3),
            "z_away": round(results["away"]["z_final"], 3),
            "tier": r["tier"], "sos": r["sos"],
            "bet": bet_type(r["components"], r["sos"]),
            "odds": odds, "ev": round(ev, 4) if ev is not None else None,
            "verdict": verdict, "flags": gate["flags"], "phase": gate["phase"],
            "r": {"z_final": r["z_final"], "comps": r["components"],
                  "ppdaValid": r["z_ppda_used"], "capped": r["rivalry_capped"]},
            "res": {s: {"z_final": results[s]["z_final"]} for s in results},
            "managers": {s: results[s]["manager"] for s in results}, "meta": meta}
