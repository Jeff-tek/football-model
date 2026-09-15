"""Tests for ingest/polymarket_free.py — mocked HTTP, no network."""

from unittest.mock import patch, MagicMock

SEARCH_HIT = {
    "events": [{
        "title": "Rayo Vallecano de Madrid vs. RCD Espanyol de Barcelona",
        "slug": "rayo-espanyol-2026-09-15",
        "closed": False,
        "endDate": "2026-09-15T17:00:00Z",
        # Live API returns these as JSON-encoded strings, not arrays.
        "markets": [
            {"question": "Will Rayo Vallecano de Madrid win on 2026-09-15?",
             "outcomes": '["Yes", "No"]', "outcomePrices": '["0.405", "0.595"]',
             "volume": "35401.4"},
            {"question": "Will Rayo Vallecano de Madrid vs. RCD Espanyol de Barcelona end in a draw?",
             "outcomes": '["Yes", "No"]', "outcomePrices": '["0.285", "0.715"]',
             "volume": "4486.5"},
            {"question": "Will RCD Espanyol de Barcelona win on 2026-09-15?",
             "outcomes": '["Yes", "No"]', "outcomePrices": '["0.315", "0.685"]',
             "volume": "84954.9"},
        ],
    }]
}

SEARCH_STALE = {
    "events": [{
        "title": "Rayo Vallecano de Madrid vs. RCD Espanyol de Barcelona",
        "slug": "rayo-espanyol-2026-04-23",
        "closed": True,
        "endDate": "2026-04-23T18:00:00Z",
        "markets": [],
    }]
}


def _mock_json(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    return r


@patch("ingest.polymarket_free.requests.get")
def test_crowd_lookup_hit(mock_get):
    mock_get.return_value = _mock_json(SEARCH_HIT)
    from ingest import polymarket_free as pm
    pm._cache.clear()
    c = pm.crowd_lookup("Rayo Vallecano", "Espanyol", "2026-09-15T17:00Z")
    assert c is not None
    assert abs(c["home"] - 0.405) < 1e-9
    assert abs(c["draw"] - 0.285) < 1e-9
    assert abs(c["away"] - 0.315) < 1e-9
    assert c["low_volume"] is True  # draw leg under $5k
    assert c["url"] == "https://polymarket.com/event/rayo-espanyol-2026-09-15"


@patch("ingest.polymarket_free.requests.get")
def test_crowd_lookup_skips_closed(mock_get):
    mock_get.return_value = _mock_json(SEARCH_STALE)
    from ingest import polymarket_free as pm
    pm._cache.clear()
    assert pm.crowd_lookup("Rayo Vallecano", "Espanyol", "2026-09-15T17:00Z") is None


@patch("ingest.polymarket_free.requests.get")
def test_crowd_lookup_no_match(mock_get):
    mock_get.return_value = _mock_json({"events": []})
    from ingest import polymarket_free as pm
    pm._cache.clear()
    assert pm.crowd_lookup("Rayo Vallecano", "Espanyol", "2026-09-15T17:00Z") is None


@patch("ingest.polymarket_free.requests.get")
def test_crowd_failure_never_raises(mock_get):
    import requests as _req
    mock_get.side_effect = _req.exceptions.Timeout()
    from ingest import polymarket_free as pm
    pm._cache.clear()
    assert pm.crowd_lookup("Rayo Vallecano", "Espanyol", "2026-09-15T17:00Z") is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")
