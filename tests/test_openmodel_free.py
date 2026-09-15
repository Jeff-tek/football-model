"""Tests for ingest/openmodel_free.py — mocked HTTP, no network."""

from unittest.mock import patch, MagicMock

ELO_CSV = """league,slug,club,elo
la-liga,rayo-vallecano,"Rayo Vallecano",1694.8
la-liga,espanyol,"Espanyol",1630.6
premier-league,brentford,"Brentford",1844.1
"""

PRED_CSV = """kickoff,league,home,away,pHome,pDraw,pAway,modelPick,lockedOn,homeGoals,awayGoals,result,correct
2099-09-15T17:00:00+00:00,la-liga,"Rayo Vallecano","Espanyol",0.42,0.28,0.30,home,2099-09-14,,,,,
2026-08-15T17:30:00+00:00,la-liga,"Alaves","Getafe",0.38,0.28,0.34,home,2026-08-15,3,0,home,true
"""


def _mock_text(payload):
    r = MagicMock()
    r.status_code = 200
    r.text = payload
    r.raise_for_status = MagicMock()
    return r


@patch("ingest.openmodel_free.requests.get")
def test_elo_lookup_fuzzy_names(mock_get):
    mock_get.return_value = _mock_text(ELO_CSV)
    from ingest import openmodel_free as om
    om._cache.clear()
    assert om.elo_lookup("La Liga", "Rayo", "Espanyol") == (1694.8, 1630.6)


@patch("ingest.openmodel_free.requests.get")
def test_elo_lookup_wrong_league_rejected(mock_get):
    mock_get.return_value = _mock_text(ELO_CSV)
    from ingest import openmodel_free as om
    om._cache.clear()
    assert om.elo_lookup("Premier League", "Rayo", "Espanyol") is None


@patch("ingest.openmodel_free.requests.get")
def test_prediction_lookup_skips_resulted(mock_get):
    mock_get.return_value = _mock_text(PRED_CSV)
    from ingest import openmodel_free as om
    om._cache.clear()
    hit = om.prediction_lookup("La Liga", "Rayo Vallecano", "Espanyol")
    assert hit is not None
    assert abs(hit["home"] - 0.42) < 1e-9
    assert hit["pick"] == "home"
    assert om.prediction_lookup("La Liga", "Alaves", "Getafe") is None


@patch("ingest.openmodel_free.requests.get")
def test_fetch_failure_never_raises(mock_get):
    import requests as _req
    mock_get.side_effect = _req.exceptions.ConnectionError("down")
    from ingest import openmodel_free as om
    om._cache.clear()
    assert om.elo_lookup("La Liga", "Rayo", "Espanyol") is None
    assert om.prediction_lookup("La Liga", "Rayo", "Espanyol") is None
    assert om.elo_table() == {}


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
