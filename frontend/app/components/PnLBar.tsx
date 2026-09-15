"use client";
import { useEffect, useState } from "react";
import { getLive } from "../lib/tips";
import { byMonth, loadLedger, settle, summarize, type Settled } from "../lib/ledger";

const LEAGUES = ["La Liga", "Premier League", "Serie A", "Bundesliga", "Ligue 1"];

const fmtU = (u: number): string => `${u > 0 ? "+" : ""}${u.toFixed(2)}u`;

export default function PnLBar({ refreshKey }: { refreshKey?: string }) {
  const [settled, setSettled] = useState<Settled[]>([]);
  const [note, setNote] = useState("");

  useEffect(() => {
    let live = true;
    (async () => {
      const entries = loadLedger();
      if (entries.length === 0) return;
      try {
        const boards = (await Promise.all(LEAGUES.map((l) => getLive(l)))).flat();
        if (live) setSettled(settle(entries, boards));
      } catch {
        if (live) {
          setSettled(entries.map((e) => ({ ...e, outcome: "pending" as const, profit: null })));
          setNote("results feed unreachable — showing recorded stakes only");
        }
      }
    })();
    return () => { live = false; };
  }, [refreshKey]);

  if (settled.length === 0 && !note) return null;
  const w = summarize(settled.length > 0 ? settled : loadLedger().map((e) => ({ ...e, outcome: "pending" as const, profit: null })), 30);
  const months = byMonth(settled);

  return (
    <section className="pnl-bar" aria-label="Profit and loss">
      <div className="pnl-head">
        <span className="pnl-title">30-day P&amp;L</span>
        <span className="pnl-window">{w.start} → {w.end}</span>
        <span className={`pnl-units ${w.units > 0 ? "pos" : w.units < 0 ? "neg" : ""}`}>
          {fmtU(w.units)}
        </span>
      </div>
      <div className="pnl-meta">
        <span>{w.bets} bets · {w.wins}W–{w.losses}L–{w.pending} pending</span>
        <span>{w.roi !== null ? `ROI ${w.roi > 0 ? "+" : ""}${w.roi}% on ${w.staked} settled @1u` : "no settled 1X2 bets yet"}</span>
        {note && <span>{note}</span>}
      </div>
      {months.length > 0 && (
        <div className="pnl-months">
          {months.map((m) => (
            <span key={m.month} className="pnl-chip">
              {m.month} · {m.bets} · {fmtU(m.units)}
            </span>
          ))}
        </div>
      )}
      <div className="pnl-fine">Flat 1u on BET/MARGINAL picks. Units count 1X2 only — free feed has no O2.5/BTTS book odds.</div>
    </section>
  );
}
