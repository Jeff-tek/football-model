from engine.module2_metrics import GK_DELTA

WEIGHTS = {"xg": 0.25, "form": 0.25, "ppda": 0.35, "inj": 0.10, "gk": 0.05}


def venue_blend(z_home, z_away, is_home, neutral=False):
    if z_home is None:
        return z_away
    if z_away is None:
        return z_home
    if neutral:
        return 0.5 * z_home + 0.5 * z_away
    return (0.7 * z_home + 0.3 * z_away) if is_home else (0.7 * z_away + 0.3 * z_home)


def composite(z_xgdev, z_form, z_ppda, z_inj, gk_delta, include_ppda=True):
    z_xgdev = z_xgdev or 0.0
    z_form = z_form or 0.0
    z_inj = z_inj or 0.0
    gk_delta = gk_delta or 0.0
    w = dict(WEIGHTS)
    if not include_ppda or z_ppda is None:
        rest = w["xg"] + w["form"] + w["inj"] + w["gk"]
        scale = 1 / rest
        w = {k: (0.0 if k == "ppda" else v * scale) for k, v in w.items()}
        z_ppda = 0.0
    return (w["xg"] * z_xgdev + w["form"] * z_form + w["ppda"] * z_ppda
            + w["inj"] * z_inj + w["gk"] * gk_delta)


def apply_modifiers(z, h2h_signal="NEUTRAL", rivalry=False):
    if h2h_signal == "ADVANTAGE":
        z *= 1.05
    elif h2h_signal == "DISADVANTAGE":
        z *= 0.95
    capped = False
    if rivalry and abs(z) > 1.5:
        z = 1.5 if z > 0 else -1.5
        capped = True
    return {"z": z, "rivalry_capped": capped}
