"use client";
import { useCallback, useEffect, useState } from "react";
import { getTips, type Tip, type TipsResponse } from "../lib/tips";

const LEAGUES = ["La Liga", "Premier League", "Serie A", "Bundesliga",
  "Ligue 1", "Russian Premier League"];

function fmtDate(iso: string): string {
  if (!iso) return "TBD";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 16).replace("T", " ");
  return d.toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function pct(p: number): string {
  return `${(p * 100).toFixed(0)}%`;
}

function TipCard({ t }: { t: Tip }) {
  const vc = t.verdict === "BET" ? "bet" : t.verdict === "MARGINAL" ? "marginal" : "nobet";
  const edgePos = t.edge.value > 0;
  const [ph, pd, pa] = t.probs["1X2"];
  const [fh, fd, fa] = t.fair["1X2"];
  return (
    <article className="tip-card">
      <div className="tip-top">
        <div className="tip-matchup">{t.home} <span className="vs">v</span> {t.away}</div>
        <div className="tip-meta">
          <span>{fmtDate(t.date)}</span>
          {t.homeForm && <span>Form {t.homeForm} · {t.awayForm}</span>}
          <span>xG {t.homeXG.toFixed(2)} – {t.awayXG.toFixed(2)}</span>
        </div>
      </div>
      <div className={`tip-band ${vc}`}>
        <div className="word">{t.verdict}</div>
        <div className="tip-pickbox">Pick<b>{t.pick}</b>
          <span className={`edge-badge ${edgePos ? "pos" : "neg"}`}>
            {edgePos ? `+${(t.edge.value * 100).toFixed(1)}%` : "no edge"}
          </span>
        </div>
      </div>
      <div className="tip-body">
        <div className="prob-grid">
          <div className="prob-cell"><div className="prob-label">1</div>
            <div className="prob-val">{pct(ph)} <small>fair {pct(fh)}</small></div></div>
          <div className="prob-cell"><div className="prob-label">X</div>
            <div className="prob-val">{pct(pd)} <small>fair {pct(fd)}</small></div></div>
          <div className="prob-cell"><div className="prob-label">2</div>
            <div className="prob-val">{pct(pa)} <small>fair {pct(fa)}</small></div></div>
          <div className="prob-cell"><div className="prob-label">O2.5</div>
            <div className="prob-val">{pct(t.probs["O2.5"])}</div></div>
          <div className="prob-cell"><div className="prob-label">BTTS</div>
            <div className="prob-val">{pct(t.probs.BTTS)}</div></div>
          <div className="prob-cell"><div className="prob-label">Confidence</div>
            <div className="prob-val">{t.confidence.toFixed(0)}%</div></div>
        </div>
        <div className="tip-reasons">
          {t.reasons.map(r => <div key={r} className="tip-reason">{r}</div>)}
        </div>
        <div className="source-links">
          {t.sources.map(s => (
            <a key={s.name} className="source-link" href={s.url} target="_blank" rel="noreferrer">{s.name}</a>
          ))}
        </div>
      </div>
    </article>
  );
}

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
          <div className="kicker">Free auto-pull · Poisson + implied odds</div>
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