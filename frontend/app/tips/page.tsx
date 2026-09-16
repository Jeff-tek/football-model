"use client";
import { useCallback, useEffect, useState } from "react";
import { getTips, type TipsResponse } from "../lib/tips";
import { recordTips } from "../lib/ledger";
import TipCard, { fmtDate } from "../components/TipCard";
import PnLBar from "../components/PnLBar";

const LEAGUES = ["La Liga", "Premier League", "Serie A", "Bundesliga", "Ligue 1"];

export default function TipsPage() {
  const [league, setLeague] = useState(LEAGUES[0]);
  const [boards, setBoards] = useState<Record<string, TipsResponse>>({});
  const [seq, setSeq] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setErr("");
    const results = await Promise.allSettled(LEAGUES.map((l) => getTips(l)));
    const next: Record<string, TipsResponse> = {};
    const failed: string[] = [];
    results.forEach((r, i) => {
      if (r.status === "fulfilled") {
        next[LEAGUES[i]] = r.value;
        recordTips(LEAGUES[i], r.value.tips);
      } else {
        failed.push(LEAGUES[i]);
      }
    });
    setBoards(next);
    setSeq((s) => s + 1);
    setUpdatedAt(Date.now());
    if (failed.length > 0) setErr(`couldn't load: ${failed.join(", ")}`);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15 * 60 * 1000);
    return () => clearInterval(id);
  }, [load]);

  const data = boards[league] ?? null;
  const total = Object.values(boards).reduce((s, b) => s + b.tips.length, 0);

  return (
    <main className="wrap">
      <header className="masthead tips-head">
        <div>
          <div className="kicker">Free auto-pull · Poisson + Elo + Open Model ensemble</div>
          <h1 className="title">Tips</h1>
        </div>
        <div className="tips-controls">
          <button className="refresh" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>
      </header>

      <div className="league-tabs" role="tablist" aria-label="Leagues">
        {LEAGUES.map((l) => (
          <button
            key={l}
            role="tab"
            aria-selected={l === league}
            className={`league-tab ${l === league ? "active" : ""}`}
            onClick={() => setLeague(l)}
          >
            {l}
            <span className="tab-count">{boards[l]?.tips.length ?? "–"}</span>
          </button>
        ))}
      </div>

      {data && (
        <p className="tips-meta">
          {data.league} · as of {fmtDate(data.as_of)} · cached {data.ttl}s · daily cron {data.cron.split(": ")[1]}
          {total > 0 && ` · ${total} tips across leagues`}
          {updatedAt != null && !loading && ` · updated ${new Date(updatedAt).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`}
        </p>
      )}
      <PnLBar refreshKey={String(seq)} />

      {loading && <div className="empty">Pulling live scoreboards + odds…</div>}
      {err && <p className="err">{err}</p>}
      {!loading && !err && data && data.tips.length === 0 && (
        <div className="empty">No fixtures with odds right now. Try another league or refresh later.</div>
      )}
      {!loading && !err && data && data.tips.length > 0 && (
        <div className="tips-list">
          {data.tips.map(t => <TipCard key={`${t.home}-${t.away}`} t={t} />)}
        </div>
      )}

      <div className="disclaimer">
        <b>Responsible gambling.</b> These tips are model output from free data, not financial advice.
        Odds move — re-check before betting. No props are included free; treat all prop markets as manual.
        If gambling stops being fun, seek help: <a className="source-link" href="https://www.begambleaware.org" target="_blank" rel="noreferrer">BeGambleAware</a>.
      </div>
    </main>
  );
}
