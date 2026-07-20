import requests
from datetime import datetime, timezone

TRANSFERMARKET_LEAGUES = {
    "Premier League": "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1",
    "La Liga": "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1",
    "Serie A": "https://www.transfermarkt.com/serie-a/startseite/wettbewerb/IT1",
    "Bundesliga": "https://www.transfermarkt.com/bundesliga/startseite/wettbewerb/L1",
    "Ligue 1": "https://www.transfermarkt.com/ligue-1/startseite/wettbewerb/FR1",
    "Russian Premier League": "https://www.transfermarkt.com/premier-liga/startseite/wettbewerb/RU1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.5",
}


def _parse_transfermarkt(html, league):
    import re
    now = datetime.now(timezone.utc).isoformat()
    out = []
    pattern = r'<div class="box">.*?<td class="hauptlink no-border-links.*?<a[^>]*>([^<]+)</a>.*?<td class="trainer">.*?<a[^>]*>([^<]+)</a>.*?<td class="appointed">.*?<td[^>]*>([^<]*)</td>'
    for m in re.finditer(pattern, html, re.DOTALL):
        team = m.group(1).strip()
        name = m.group(2).strip()
        appointed = m.group(3).strip()
        is_caretaker = "caretaker" in html[max(0, m.start() - 200):m.start()].lower()
        out.append({
            "league": league, "team": team, "name": name,
            "appointed_on": appointed if appointed else None,
            "is_caretaker": is_caretaker, "scraped_at": now,
        })
    return out


def _parse_table_rows(html, league):
    import re
    now = datetime.now(timezone.utc).isoformat()
    out = []
    club_pat = re.compile(r'<td[^>]*class="hauptlink[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', re.DOTALL)
    trainer_pat = re.compile(r'<td[^>]*class="trainer"[^>]*>.*?<a[^>]*>([^<]+)</a>', re.DOTALL)
    clubs = club_pat.findall(html)
    trainers = trainer_pat.findall(html)
    for i, name in enumerate(clubs):
        if i < len(trainers):
            out.append({
                "league": league, "team": name.strip(), "name": trainers[i].strip(),
                "appointed_on": None, "is_caretaker": False, "scraped_at": now,
            })
    return out


def fetch_managers(league):
    url = TRANSFERMARKET_LEAGUES.get(league)
    if not url:
        return []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        managers = _parse_table_rows(r.text, league)
        if not managers:
            managers = _parse_transfermarkt(r.text, league)
        return managers
    except Exception:
        return []


def fetch_all_managers():
    out = []
    for league in TRANSFERMARKET_LEAGUES:
        mgrs = fetch_managers(league)
        out.extend(mgrs)
        if mgrs:
            print(f"  {league}: {len(mgrs)} managers")
        else:
            print(f"  {league}: failed to scrape")
    return out
