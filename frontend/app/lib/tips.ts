const API = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export type TeamMeta = {
  team: string;
  rank: number | null;
  points: number | null;
  played: number | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  gf: number | null;
  ga: number | null;
} | null;

export type Tip = {
  home: string;
  away: string;
  date: string;
  probs: {
    "1X2": [number, number, number];
    DC: [number, number, number];
    "O2.5": number;
    "U2.5": number;
    BTTS: number;
  };
  fair: { "1X2": [number, number, number] };
  edge: { market: string; value: number };
  pick: string;
  verdict: "BET" | "MARGINAL" | "NO BET" | "PASS";
  reasons: string[];
  confidence: number;
  models: string[];
  crowd: {
    home: number;
    draw: number;
    away: number;
    volumes: { home: number; draw: number; away: number };
    url: string;
    low_volume: boolean;
  } | null;
  lineMove: { Home?: string; Draw?: string; Away?: string } | null;
  crowdTrend?: {
    homeDelta: number;
    drawDelta: number;
    awayDelta: number;
    since: string;
  } | null;
  sources: { name: string; url: string }[];
  homeForm: string;
  awayForm: string;
  homeXG: number;
  awayXG: number;
  bookOdds: { home: number | null; draw: number | null; away: number | null };
  teamMeta?: { home: TeamMeta; away: TeamMeta };
};

export type TipsResponse = {
  league: string;
  as_of: string;
  ttl: number;
  cron: string;
  tips: Tip[];
};

export async function getTips(league: string): Promise<TipsResponse> {
  const r = await fetch(`${API}/tips?league=${encodeURIComponent(league)}`, { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type LiveScore = {
  home: string; away: string; home_score: number | null;
  away_score: number | null; state: string;
};

export async function getLive(league: string): Promise<LiveScore[]> {
  const r = await fetch(`${API}/live?league=${encodeURIComponent(league)}`, { cache: "no-store" });
  if (!r.ok) return [];
  return r.json();
}