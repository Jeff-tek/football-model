import { getTips, type Tip } from "./tips";

export const TOP_LEAGUES = [
  "Premier League",
  "La Liga",
  "Serie A",
  "Bundesliga",
  "Ligue 1",
] as const;

export type LeagueGroup = { league: string; tips: Tip[]; asOf: string };

const sameLocalDay = (iso: string, ref = new Date()): boolean => {
  if (!iso) return false;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  return (
    d.getFullYear() === ref.getFullYear() &&
    d.getMonth() === ref.getMonth() &&
    d.getDate() === ref.getDate()
  );
};

export async function getTodayMatches(): Promise<LeagueGroup[]> {
  const settled = await Promise.allSettled(TOP_LEAGUES.map((lg) => getTips(lg)));
  return TOP_LEAGUES.map((league, i) => {
    const r = settled[i];
    if (r.status !== "fulfilled") return { league, tips: [], asOf: "" };
    const today = r.value.tips.filter((t) => sameLocalDay(t.date));
    today.sort((a, b) => +new Date(a.date) - +new Date(b.date));
    return { league, tips: today, asOf: r.value.as_of };
  });
}
