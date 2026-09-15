import type { LiveScore, Tip } from "./tips";

export type LedgerEntry = {
  id: string; league: string; home: string; away: string;
  date: string; pick: string; verdict: string;
  odds: number | null; placedAt: string;
};

export type Settled = LedgerEntry & {
  outcome: "win" | "loss" | "pending";
  profit: number | null;
};

const KEY = "tips-ledger-v1";
const norm = (s: string): string => (s || "").trim().toLowerCase();
const idOf = (league: string, t: Tip): string =>
  [league, t.home, t.away, t.date, t.pick].map(norm).join("|");

const pickOdds = (t: Tip): number | null => {
  const b = t.bookOdds;
  if (!b) return null;
  if (t.pick === "Home") return b.home;
  if (t.pick === "Draw") return b.draw;
  if (t.pick === "Away") return b.away;
  return null; // free feed carries 1X2 odds only — no honest units for O2.5/BTTS/DC
};

export const loadLedger = (): LedgerEntry[] => {
  try {
    const raw = localStorage.getItem(KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
};

export const recordTips = (league: string, tips: Tip[]): LedgerEntry[] => {
  const now = new Date().toISOString();
  const seen = new Set(loadLedger().map((e) => e.id));
  const fresh = tips
    .filter((t) => t.verdict === "BET" || t.verdict === "MARGINAL")
    .filter((t) => !seen.has(idOf(league, t)))
    .map((t) => ({
      id: idOf(league, t), league, home: t.home, away: t.away,
      date: t.date, pick: t.pick, verdict: t.verdict,
      odds: pickOdds(t), placedAt: now,
    }));
  if (fresh.length === 0) return loadLedger();
  const next = [...loadLedger(), ...fresh].slice(-500);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch { /* private mode — ledger stays in memory */ }
  return next;
};

export const gradePick = (pick: string, h: number, a: number): boolean | null => {
  if (pick === "Home") return h > a;
  if (pick === "Draw") return h === a;
  if (pick === "Away") return h < a;
  if (pick === "1X") return h >= a;
  if (pick === "12") return h !== a;
  if (pick === "X2") return h <= a;
  if (pick === "Over 2.5") return h + a >= 3;
  if (pick === "Under 2.5") return h + a <= 2;
  if (pick === "BTTS Yes") return h > 0 && a > 0;
  if (pick === "BTTS No") return h === 0 || a === 0;
  return null;
};

export const settle = (entries: LedgerEntry[], boards: LiveScore[]): Settled[] => {
  const byGame = new Map(
    boards
      .filter((m) => m.state === "post" && m.home_score !== null && m.away_score !== null)
      .map((m) => [`${norm(m.home)}|${norm(m.away)}`, m]),
  );
  return entries.map((e) => {
    const m = byGame.get(`${norm(e.home)}|${norm(e.away)}`);
    if (!m) return { ...e, outcome: "pending" as const, profit: null };
    const won = gradePick(e.pick, m.home_score as number, m.away_score as number);
    if (won === null || e.odds === null) {
      return { ...e, outcome: won === null ? ("pending" as const) : (won ? ("win" as const) : ("loss" as const)), profit: null };
    }
    return { ...e, outcome: won ? ("win" as const) : ("loss" as const), profit: won ? e.odds - 1 : -1 };
  });
};

export type Window = {
  bets: number; wins: number; losses: number; pending: number;
  units: number; staked: number; roi: number | null; start: string; end: string;
};

export const summarize = (settled: Settled[], days: number, now = new Date()): Window => {
  const end = now.toISOString().slice(0, 10);
  const start = new Date(now.getTime() - days * 864e5).toISOString().slice(0, 10);
  const inWin = settled.filter((e) => e.placedAt.slice(0, 10) >= start);
  const dec = inWin.filter((e) => e.profit !== null);
  const units = dec.reduce((s, e) => s + (e.profit as number), 0);
  return {
    bets: inWin.length,
    wins: inWin.filter((e) => e.outcome === "win").length,
    losses: inWin.filter((e) => e.outcome === "loss").length,
    pending: inWin.filter((e) => e.outcome === "pending").length,
    units: Math.round(units * 100) / 100,
    staked: dec.length,
    roi: dec.length > 0 ? Math.round((units / dec.length) * 1000) / 10 : null,
    start, end,
  };
};

export const byMonth = (settled: Settled[]): { month: string; bets: number; units: number }[] => {
  const acc = new Map<string, { bets: number; units: number }>();
  for (const e of settled) {
    const month = e.placedAt.slice(0, 7);
    const cur = acc.get(month) ?? { bets: 0, units: 0 };
    cur.bets += 1;
    if (e.profit !== null) cur.units = Math.round((cur.units + e.profit) * 100) / 100;
    acc.set(month, cur);
  }
  return [...acc.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .slice(0, 6)
    .map(([month, v]) => ({ month, ...v }));
};
