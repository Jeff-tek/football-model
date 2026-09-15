"use client";
import { useCallback, useEffect, useState } from "react";
import { getTips, type TipsResponse } from "../lib/tips";
import TipCard, { fmtDate } from "../components/TipCard";

const LEAGUES = ["La Liga", "Premier League", "Serie A", "Bundesliga",
  "Ligue 1", "Russian Premier League"];

export default function TipsPage() {
  const [league, setLeague] = useState(LEAGUES[0]);
  const [data, setData] = useState<TipsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = useCallback(async (lg: string) => {
    setLoading(true); setErr("");
    try {
      setData(await getTips(lg));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed to load tips");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(league); }, [league, load]);

  return (
    <main className="wrap">
      <header className="masthead tips-head">
        <div>
          <div className="kicker">Free auto-pull · Poisson + Elo + Open Model ensemble</div>
          <h1 className="title">Today&apos;s Tips</h1>
        </div>
        <div className="tips-controls">
          <select value={league} onChange={e => setLeague(e.target.value)} aria-label="League">
            {LEAGUES.map(l => <option key={l}>{l}</option>)}
          </select>
          <button className="refresh" onClick={() => load(league)} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </header>

      {data && (
        <p className="tips-meta">
          {data.league} · as of {fmtDate(data.as_of)} · cached {data.ttl}s · daily cron {data.cron.split(": ")[1]}
        </p>
      )}

      {loading && <div className="empty">Pulling live scoreboard + odds…</div>}
      {err && <p className="err">{err}</p>}
      {!loading && !err && data && data.tips.length === 0 && (
        <div className="empty">No fixtures with odds right now. Try another league or refresh later.</div>
      )}
      {!loading && !err && data && data.tips.length > 0 && (
        <div className="tips-list">
          {data.tips.map(t => <TipCard key={`${t.home}-${t.away}`} t={t} />)}
        </div>
      )}

      <div className="props-note">
        <b>Player props — manual check.</b> Free feeds (ESPN / OpenLigaDB) carry no player props.
        Before any prop bet, verify manually:
        <ul>
          <li>Lineup / team news 60 min before kickoff</li>
          <li>Goalscorer form + minutes played trend</li>
          <li>Bookmaker prop odds vs your own estimate</li>
        </ul>
      </div>

      <div className="disclaimer">
        <b>Responsible gambling.</b> These tips are model output from free data, not financial advice.
        Odds move — re-check before betting. No props are included free; treat all prop markets as manual.
        If gambling stops being fun, seek help: <a className="source-link" href="https://www.begambleaware.org" target="_blank" rel="noreferrer">BeGambleAware</a>.
      </div>
    </main>
  );
}
