def season_phase_gate(matchweek, sample):
    if sample < 5:
        return {"proceed": False, "phase": None, "flags": [],
                "msg": "INSUFFICIENT DATA — NO BET"}
    flags = []
    if sample < 10:
        flags.append("REDUCED SAMPLE — LOWER CONFIDENCE")
    phase = "Early" if matchweek <= 8 else "Mid" if matchweek <= 30 else "Late"
    if phase == "Late":
        flags.append("Check rotation/squad risk if standings decided")
    return {"proceed": True, "phase": phase, "flags": flags, "msg": None}


def manager_gate(weeks_in_post, is_caretaker=False):
    if is_caretaker:
        return {"discard_ppda": True, "downgrade": True, "status": "Caretaker"}
    if weeks_in_post is not None and weeks_in_post < 6:
        return {"discard_ppda": True, "downgrade": False, "status": "In transition"}
    return {"discard_ppda": False, "downgrade": False, "status": "Stable"}
