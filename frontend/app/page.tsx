"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getTodayMatches, type LeagueGroup } from "./lib/today";
import TipCard, { fmtDate } from "./components/TipCard";

export default function Today() {
  const [groups, setGroups] = useState<LeagueGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      setGroups(await getTodayMatches());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed to load matches");
      setGroups([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const total = groups.reduce((n, g) => n + g.tips.length, 0);
  const todayLabel = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <main className="wrap">
      <header className="masthead tips-head">
        <div>
          <div className="kicker">Top 5 leagues · updates daily on load</div>
          <h1 className="title">Today&apos;s Matches</h1>
          <p className="tips-meta">
            {todayLabel} · {loading ? "loading…" : `${total} match${total === 1 ? "" : "es"} today`}
          </p>
        </div>
        <div className="tips-controls">
          <button className="refresh" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          <Link className="source-link" href="/tips">
            All tips
          </Link>
          <Link className="source-link" href="/desk">
            Model Desk
          </Link>
        </div>
      </header>

      {loading && <div className="empty">Loading today&apos;s matches across top leagues…</div>}
      {err && <p className="err">{err}</p>}

      {!loading && !err && total === 0 && (
        <div className="empty">
          No matches with odds today. Check back later — or browse{" "}
          <Link className="source-link" href="/tips">
            all tips
          </Link>
          .
        </div>
      )}

      {!loading &&
        !err &&
        groups.map(
          (g) =>
            g.tips.length > 0 && (
              <section key={g.league}>
                <div className="eyebrow">
                  <span className="num">{g.tips.length}</span> {g.league}
                </div>
                <div className="today-list">
                  {g.tips.map((t) => {
                    const key = `${g.league}:${t.home}-${t.away}`;
                    const isOpen = open === key;
                    return (
                      <div key={key} className="today-row">
                        <button
                          className="today-btn"
                          onClick={() => setOpen(isOpen ? null : key)}
                          aria-expanded={isOpen}
                        >
                          <span className="today-matchup">
                            {t.home} <span className="vs">v</span> {t.away}
                          </span>
                          <span className="today-right">
                            <span className="today-time">{fmtDate(t.date)}</span>
                            <span className={`verdict-pill ${t.verdict === "BET" ? "bet" : t.verdict === "MARGINAL" ? "marginal" : "nobet"}`}>
                              {t.verdict}
                            </span>
                            <span className="today-chev">{isOpen ? "▾" : "▸"}</span>
                          </span>
                        </button>
                        {isOpen && (
                          <div className="today-tip">
                            <TipCard t={t} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )
        )}

      <div className="disclaimer">
        <b>Responsible gambling.</b> Model output from free data, not financial advice.
        Odds move — re-check before betting. If gambling stops being fun, seek help:{" "}
        <a className="source-link" href="https://www.begambleaware.org" target="_blank" rel="noreferrer">
          BeGambleAware
        </a>
        .
      </div>
    </main>
  );
}
