import { getTips, type Tip } from "./tips";

export const TOP_LEAGUES = [
  "Premier League",
  "La Liga",
  "Serie A",
  "Bundesliga",
  "Ligue 1",
] as const;

export type LeagueGroup = { league: string; tips: Tip[]; asOf: string };

export async function getTodayMatches(): Promise<LeagueGroup[]> {
  const settled = await Promise.allSettled(TOP_LEAGUES.map((lg) => getTips(lg)));
  return TOP_LEAGUES.map((league, i) => {
    const r = settled[i];
    if (r.status !== "fulfilled") return { league, tips: [], asOf: "" };
    const tips = [...r.value.tips];
    tips.sort((a, b) => +new Date(a.date) - +new Date(b.date));
    return { league, tips, asOf: r.value.as_of };
  });
}
