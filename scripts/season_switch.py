"""Season switch: update env vars and re-ingest for a new season.

Usage:
    # Auto-detect next season (2026-2027 → 2027-2028)
    python3 scripts/season_switch.py

    # Explicit new season
    python3 scripts/season_switch.py 2026-2027

    # Dry-run mode (just prints what it would do)
    python3 scripts/season_switch.py --dry-run

Vercel Hobby users: the full ingest will timeout. After running locally
or with --dry-run, use the printed curl commands to trigger per-league
ingests on Vercel (each stays under 10s for leagues with 0 new matches).
"""

import os, sys, re, subprocess

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

LEAGUES = ["Premier+League", "La+Liga", "Serie+A", "Bundesliga", "Ligue+1",
           "Russian+Premier+League"]


def parse_season_arg():
    if len(sys.argv) >= 2 and sys.argv[1] != "--dry-run":
        return sys.argv[1]
    fbref = os.environ.get("CURRENT_SEASON_FBREF", "2025-2026")
    parts = fbref.split("-")
    if len(parts) != 2:
        print(f"ERROR: cannot parse CURRENT_SEASON_FBREF={fbref!r}")
        sys.exit(1)
    start = int(parts[0]) + 1
    return f"{start}-{start + 1}"


def season_vars(fbref):
    parts = fbref.split("-")
    understat = parts[0]
    return understat, fbref


def update_dotenv(understat, fbref):
    if not os.path.isfile(ENV_PATH):
        print(f"  .env not found at {ENV_PATH}, skipping")
        return
    with open(ENV_PATH) as f:
        content = f.read()
    content = re.sub(r'^CURRENT_SEASON_UNDERSTAT=.*', f'CURRENT_SEASON_UNDERSTAT={understat}',
                     content, flags=re.MULTILINE)
    content = re.sub(r'^CURRENT_SEASON_FBREF=.*', f'CURRENT_SEASON_FBREF={fbref}',
                     content, flags=re.MULTILINE)
    with open(ENV_PATH, "w") as f:
        f.write(content)
    print(f"  Updated .env: UNDERSTAT={understat}, FBREF={fbref}")


def run_pipeline(fbref):
    print("  Running full ingest pipeline...")
    env = os.environ.copy()
    env["CURRENT_SEASON_UNDERSTAT"] = fbref.split("-")[0]
    env["CURRENT_SEASON_FBREF"] = fbref
    result = subprocess.run(
        [sys.executable, "-m", "ingest.run_all"],
        cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=600)
    print(result.stdout)
    if result.returncode != 0:
        print(f"  WARN: pipeline exited {result.returncode}")
        print(result.stderr[-1000:] if result.stderr else "")


def main():
    dry_run = "--dry-run" in sys.argv
    new_fbref = parse_season_arg()
    understat, fbref = season_vars(new_fbref)

    print(f"Season switch: {fbref}")
    print(f"  Understat season: {understat}")
    print(f"  FBref season:     {fbref}")
    print()

    if dry_run:
        print("[DRY RUN — no changes made]")
    else:
        update_dotenv(understat, fbref)

    print()
    print("Steps:")
    print(f"  1. Update CURRENT_SEASON_UNDERSTAT={understat}")
    print(f"  2. Update CURRENT_SEASON_FBREF={fbref}")
    short = fbref.split("-")[1][2:]
    print(f"  3. Re-scrape managers from Wikipedia {understat}–{short} pages")
    print(f"  4. Re-ingest Understat matches + recompute distributions")
    print(f"  5. Refresh FPL injuries and odds")
    print()

    print()
    print("Vercel env update commands (run in terminal):")
    print(f'  vercel env rm CURRENT_SEASON_UNDERSTAT && vercel env add CURRENT_SEASON_UNDERSTAT {understat}')
    print(f'  vercel env rm CURRENT_SEASON_FBREF && vercel env add CURRENT_SEASON_FBREF {fbref}')
    print(f'  vercel deploy --prod')
    print()
    cron = os.environ.get("CRON_SECRET", "15b23ade1d7b4d7851364c6b67c0729e")
    api_base = os.environ.get("NEXT_PUBLIC_API_URL", "https://football-model-phi.vercel.app")
    api_base = api_base.replace("/api", "").rstrip("/")
    print("Per-league ingest triggers (Vercel Hobby compatible <10s each):")
    for league in LEAGUES:
        print(f'  curl -H "Authorization: Bearer {cron}" "{api_base}/api/ingest?league={league}"')
    print()
    print("Or full ingest (may timeout on Hobby):")
    print(f'  curl -H "Authorization: Bearer {cron}" "{api_base}/api/ingest"')

    if not dry_run and input("Run ingest pipeline now? [y/N] ").strip().lower() == "y":
        run_pipeline(fbref)
        print("Done.")
    else:
        print("Skipped. Run later with: python3 -m ingest.run_all")


if __name__ == "__main__":
    main()
