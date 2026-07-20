import html, os
import requests, re
from datetime import datetime, timezone

LEAGUE_NAMES = {
    "Premier League": "Premier_League",
    "La Liga": "La_Liga",
    "Serie A": "Serie_A",
    "Bundesliga": "Bundesliga",
    "Ligue 1": "Ligue_1",
    "Russian Premier League": "Russian_Premier_League",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-model/1.0)"}


def _season_slug(fbref_season):
    """Convert '2025-2026' to '2025\u201326' (Wikipedia short season)."""
    parts = fbref_season.split("-")
    if len(parts) != 2:
        return fbref_season.replace("-", "\u2013")
    return f"{parts[0]}\u2013{parts[1][2:]}"


def _build_urls():
    fbref = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
    slug = _season_slug(fbref)
    return {league: f"https://en.wikipedia.org/wiki/{slug}_{name}"
            for league, name in LEAGUE_NAMES.items()}


def fetch_managers(league):
    urls = _build_urls()
    url = urls.get(league)
    if not url:
        return []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        page_html = r.text
    except Exception:
        # Fallback: try previous season
        fbref = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
        parts = fbref.split("-")
        if len(parts) == 2:
            prev = f"{int(parts[0]) - 1}-{int(parts[0])}"
            os.environ["CURRENT_SEASON_FBREF"] = prev
            return fetch_managers(league)
        return []
    try:
        tables = re.findall(r'<table[^>]*>(.*?)</table>', page_html, re.DOTALL)
        now = datetime.now(timezone.utc).isoformat()
        out = []
        for table in tables:
            rows = re.findall(r'<tr[^>]*>.*?</tr>', table, re.DOTALL)
            if len(rows) < 3:
                continue
            header_cells = re.findall(r'<th[^>]*>(.*?)</th>', rows[0], re.DOTALL)
            headers_text = [re.sub(r'<[^>]+>', '', c).strip().lower() for c in header_cells]
            if "team" in headers_text and ("manager" in headers_text or "head coach" in headers_text):
                team_idx = next(i for i, h in enumerate(headers_text) if h == "team")
                mgr_key = "manager" if "manager" in headers_text else "head coach"
                mgr_idx = next(i for i, h in enumerate(headers_text) if h == mgr_key)
                for row in rows[1:]:
                    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
                    if len(cells) <= max(team_idx, mgr_idx):
                        continue
                    club = html.unescape(re.sub(r'<[^>]+>', '', cells[team_idx]).strip())
                    mgr = html.unescape(re.sub(r'<[^>]+>', '', cells[mgr_idx]).strip())
                    club = re.sub(r'\[\w+\]', '', club).strip()
                    mgr = re.sub(r'\[\w+\]', '', mgr).strip()
                    if not club or not mgr or mgr in ("Manager", "Head coach"):
                        continue
                    out.append({
                        "league": league, "team": club, "name": mgr,
                        "appointed_on": None,
                        "is_caretaker": "caretaker" in mgr.lower() or "‡" in mgr,
                        "scraped_at": now,
                    })
                if out:
                    break
        return out
    except Exception:
        return []


def fetch_all_managers():
    out = []
    for league in LEAGUE_NAMES:
        mgrs = fetch_managers(league)
        out.extend(mgrs)
        if mgrs:
            print(f"  {league}: {len(mgrs)} managers")
        else:
            print(f"  {league}: failed")
    return out
