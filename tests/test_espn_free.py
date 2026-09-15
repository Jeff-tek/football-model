"""Tests for ingest/espn_free.py + ingest/openliga_free.py — mocked HTTP, no network.

Runnable via `python tests/test_espn_free.py` (no pytest needed) or pytest.
"""
from unittest.mock import patch, MagicMock
import requests as _req

# --- fixtures ---


def _scoreboard_resp(events=None):
    return {"events": events or []}


def _ml_leg(odds):
    return {"close": {"odds": odds}}


def _event(ev_id="1001", state="pre", home_id="86", away_id="88",
           home_name="Real Madrid", away_name="Espanyol",
           home_score="0", away_score="0",
           home_ml="+180", away_ml="+450", draw_ml="+360"):
    return {
        "id": ev_id,
        "date": "2026-09-15T20:00Z",
        "name": f"{home_name} vs {away_name}",
        "competitions": [{
            "competitors": [
                {"team": {"id": home_id, "displayName": home_name},
                 "homeAway": "home", "score": home_score, "form": "WWDWL"},
                {"team": {"id": away_id, "displayName": away_name},
                 "homeAway": "away", "score": away_score, "form": "LWLDL"},
            ],
            "status": {"type": {"state": state, "shortDetail": "Scheduled" if state == "pre" else "Final"}},
            "odds": [{"provider": {"name": "DraftKings"},
                      "details": [f"{home_name[:3].upper()} {home_ml}"],
                      "moneyline": {
                          "home": _ml_leg(home_ml),
                          "draw": _ml_leg(draw_ml),
                          "away": _ml_leg(away_ml)}}],
        }],
    }


def _standings_resp(entries=None):
    return {"children": [{"standings": {"entries": entries or []}}]}


def _standing_entry(team_id="86", team_name="Real Madrid", pts=75, gp=38,
                    wins=22, losses=8, ties=8, gf=72, ga=35):
    return {
        "team": {"id": team_id, "displayName": team_name, "shortDisplayName": team_name},
        "stats": [
            {"name": "points", "value": pts},
            {"name": "gamesPlayed", "value": gp},
            {"name": "wins", "value": wins},
            {"name": "losses", "value": losses},
            {"name": "ties", "value": ties},
            {"name": "pointsFor", "value": gf},
            {"name": "pointsAgainst", "value": ga},
        ],
    }


def _schedule_resp(events=None):
    return {"events": events or []}


def _mock_get(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    return r


def _mock_get_error(status=500):
    r = MagicMock()
    r.status_code = status
    r.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return r


# --- fetch_scoreboard tests ---

@patch("ingest.espn_free.requests.get")
def test_scoreboard_empty_events(mock_get):
    mock_get.return_value = _mock_get(_scoreboard_resp())
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert result == []
    mock_get.assert_called_once()


@patch("ingest.espn_free.requests.get")
def test_scoreboard_parses_match(mock_get):
    mock_get.return_value = _mock_get(_scoreboard_resp([_event()]))
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert len(result) == 1
    m = result[0]
    assert m["home"] == "Real Madrid"
    assert m["away"] == "Espanyol"
    assert m["home_id"] == "86"
    assert m["away_id"] == "88"
    assert m["state"] == "pre"
    assert m["home_score"] == 0
    assert m["away_score"] == 0
    assert m["odds"] == {"provider": "DraftKings",
                         "home": 2.8, "draw": 4.6, "away": 5.5}
    assert m["home_form"] == "WWDWL"
    assert m["away_form"] == "LWLDL"


@patch("ingest.espn_free.requests.get")
def test_scoreboard_live_match(mock_get):
    mock_get.return_value = _mock_get(_scoreboard_resp([_event(state="in", home_score="2", away_score="1")]))
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert result[0]["state"] == "in"
    assert result[0]["home_score"] == 2
    assert result[0]["away_score"] == 1


@patch("ingest.espn_free.requests.get")
def test_scoreboard_http_error_returns_empty(mock_get):
    mock_get.return_value = _mock_get_error(403)
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert result == []


@patch("ingest.espn_free.requests.get")
def test_scoreboard_timeout_returns_empty(mock_get):
    mock_get.side_effect = _req.exceptions.Timeout()
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert result == []


@patch("ingest.espn_free.requests.get")
def test_scoreboard_malformed_json_returns_empty(mock_get):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.side_effect = ValueError("bad json")
    mock_get.return_value = r
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert result == []


@patch("ingest.espn_free.requests.get")
def test_scoreboard_missing_odds(mock_get):
    ev = _event()
    ev["competitions"][0].pop("odds", None)
    mock_get.return_value = _mock_get(_scoreboard_resp([ev]))
    from ingest.espn_free import fetch_scoreboard
    result = fetch_scoreboard("esp.1")
    assert result[0]["odds"] == {}


@patch("ingest.espn_free.requests.get")
def test_scoreboard_no_custom_user_agent(mock_get):
    # ESPN 403s custom User-Agents; requests' default must pass through untouched.
    mock_get.return_value = _mock_get(_scoreboard_resp())
    from ingest.espn_free import fetch_scoreboard
    fetch_scoreboard("eng.1")
    _, kwargs = mock_get.call_args
    assert "User-Agent" not in kwargs.get("headers", {})


def test_american_to_decimal():
    from ingest.espn_free import american_to_decimal as d
    assert d("+135") == 2.35
    assert d("-110") == round(1 + 100 / 110, 3)
    assert d(240) == 3.4
    assert d("EVEN") == 2.0
    assert d(1.8) == 1.8
    assert d("2.5") == 2.5
    assert d(None) is None
    assert d("bogus") is None


@patch("ingest.espn_free.requests.get")
def test_scoreboard_open_fallback(mock_get):
    ev = _event()
    ml = ev["competitions"][0]["odds"][0]["moneyline"]
    ml["home"] = {"open": {"odds": "-110"}}
    mock_get.return_value = _mock_get(_scoreboard_resp([ev]))
    from ingest.espn_free import fetch_scoreboard
    assert fetch_scoreboard("esp.1")[0]["odds"]["home"] == round(1 + 100 / 110, 3)


@patch("ingest.espn_free.requests.get")
def test_scoreboard_incomplete_moneyline_skipped(mock_get):
    ev = _event()
    ev["competitions"][0]["odds"][0]["moneyline"].pop("away")
    mock_get.return_value = _mock_get(_scoreboard_resp([ev]))
    from ingest.espn_free import fetch_scoreboard
    assert fetch_scoreboard("esp.1")[0]["odds"] == {}


# --- fetch_standings tests ---

@patch("ingest.espn_free.requests.get")
def test_standings_empty(mock_get):
    mock_get.return_value = _mock_get(_standings_resp())
    from ingest.espn_free import fetch_standings
    result = fetch_standings("esp.1")
    assert result == []


@patch("ingest.espn_free.requests.get")
def test_standings_parses_entry(mock_get):
    mock_get.return_value = _mock_get(_standings_resp([_standing_entry()]))
    from ingest.espn_free import fetch_standings
    result = fetch_standings("esp.1")
    assert len(result) == 1
    s = result[0]
    assert s["team"] == "Real Madrid"
    assert s["team_id"] == "86"
    assert s["points"] == 75
    assert s["rank"] == 1


@patch("ingest.espn_free.requests.get")
def test_standings_rank_order(mock_get):
    entries = [_standing_entry(pts=75), _standing_entry(team_id="88", team_name="Espanyol", pts=40)]
    mock_get.return_value = _mock_get(_standings_resp(entries))
    from ingest.espn_free import fetch_standings
    result = fetch_standings("esp.1")
    assert result[0]["rank"] == 1
    assert result[1]["rank"] == 2


@patch("ingest.espn_free.requests.get")
def test_standings_http_error_returns_empty(mock_get):
    mock_get.return_value = _mock_get_error(502)
    from ingest.espn_free import fetch_standings
    assert fetch_standings("esp.1") == []


@patch("ingest.espn_free.requests.get")
def test_standings_missing_stat_returns_none(mock_get):
    entry = _standing_entry()
    entry["stats"] = [{"name": "points", "value": 50}]
    mock_get.return_value = _mock_get(_standings_resp([entry]))
    from ingest.espn_free import fetch_standings
    result = fetch_standings("esp.1")
    assert result[0]["points"] == 50
    assert result[0]["wins"] is None


# --- fetch_team_schedule tests ---

@patch("ingest.espn_free.requests.get")
def test_schedule_empty(mock_get):
    mock_get.return_value = _mock_get(_schedule_resp())
    from ingest.espn_free import fetch_team_schedule
    result = fetch_team_schedule("86")
    assert result == []


@patch("ingest.espn_free.requests.get")
def test_schedule_parses_result(mock_get):
    ev = _event(state="post", home_score="3", away_score="1")
    mock_get.return_value = _mock_get(_schedule_resp([ev]))
    from ingest.espn_free import fetch_team_schedule
    result = fetch_team_schedule("86")
    assert len(result) == 1
    m = result[0]
    assert m["home"] == "Real Madrid"
    assert m["home_score"] == 3
    assert m["played"] is True


@patch("ingest.espn_free.requests.get")
def test_schedule_filters_non_played(mock_get):
    mock_get.return_value = _mock_get(_schedule_resp([_event(state="pre")]))
    from ingest.espn_free import fetch_team_schedule
    result = fetch_team_schedule("86")
    assert result == []


@patch("ingest.espn_free.requests.get")
def test_schedule_http_error_returns_empty(mock_get):
    mock_get.return_value = _mock_get_error(404)
    from ingest.espn_free import fetch_team_schedule
    assert fetch_team_schedule("86") == []


# --- openliga_free tests ---

@patch("ingest.openliga_free.requests.get")
def test_openliga_empty(mock_get):
    mock_get.return_value = _mock_get([])
    from ingest.openliga_free import fetch_matches
    result = fetch_matches("bl1")
    assert result == []


@patch("ingest.openliga_free.requests.get")
def test_openliga_parses_match(mock_get):
    match = {
        "MatchID": 12345,
        "MatchDateTime": "2026-09-15T18:30:00",
        "Team1": {"TeamName": "Bayern Munich", "TeamId": 40},
        "Team2": {"TeamName": "Dortmund", "TeamId": 67},
        "MatchResults": [{"Result": {"PointsTeam1": 2, "PointsTeam2": 1}}],
        "MatchIsFinished": True,
        "Group": {"GroupName": "1. Bundesliga", "GroupOrderID": 1},
    }
    mock_get.return_value = _mock_get([match])
    from ingest.openliga_free import fetch_matches
    result = fetch_matches("bl1")
    assert len(result) == 1
    m = result[0]
    assert m["home"] == "Bayern Munich"
    assert m["away"] == "Dortmund"
    assert m["home_score"] == 2
    assert m["away_score"] == 1
    assert m["played"] is True


@patch("ingest.openliga_free.requests.get")
def test_openliga_no_results(mock_get):
    match = {
        "MatchID": 99,
        "MatchDateTime": "2026-09-20T20:00:00",
        "Team1": {"TeamName": "Team A", "TeamId": 1},
        "Team2": {"TeamName": "Team B", "TeamId": 2},
        "MatchResults": [],
        "MatchIsFinished": False,
        "Group": {"GroupName": "BL", "GroupOrderID": 1},
    }
    mock_get.return_value = _mock_get([match])
    from ingest.openliga_free import fetch_matches
    result = fetch_matches("bl1")
    assert result[0]["played"] is False
    assert result[0]["home_score"] is None


@patch("ingest.openliga_free.requests.get")
def test_openliga_http_error_returns_empty(mock_get):
    mock_get.return_value = _mock_get_error(500)
    from ingest.openliga_free import fetch_matches
    assert fetch_matches("bl1") == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t(); print(f"PASS  {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} passed")