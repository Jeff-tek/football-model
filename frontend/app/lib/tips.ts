const API = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export type Tip = {
  home: string;
  away: string;
  date: string;
  probs: { "1X2": [number, number, number]; "O2.5": number; BTTS: number };
  fair: { "1X2": [number, number, number] };
  edge: { market: string; value: number };
  pick: string;
  verdict: "BET" | "MARGINAL" | "NO BET" | "PASS";
  reasons: string[];
  confidence: number;
  sources: { name: string; url: string }[];
  homeForm: string;
  awayForm: string;
  homeXG: number;
  awayXG: number;
  bookOdds: { home: number; draw: number; away: number };
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