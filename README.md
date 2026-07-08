# Football Model

Multi-league EV-first match analysis. Free-data stack.
Backend (FastAPI + scrapers) + Postgres + Next.js frontend.

## Local quickstart
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env      # fill DATABASE_URL + ODDS_API_KEY
    python -m tests.test_engine        # should print all passed
    python -c "import db; db.init_db()"
    python ingest/run_all.py           # seed (slow: FBref crawl-delay)
    uvicorn api.main:app --reload      # API at :8000

    cd frontend
    npm install
    cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL
    npm run dev                        # UI at :3000

## Deploy
DB on Neon, backend+cron on Railway, frontend on Vercel (root dir = frontend).
See the ClickUp doc "Football Model — Codebase" for the full step-by-step.
