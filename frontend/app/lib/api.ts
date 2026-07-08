const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getTeams(league: string): Promise<string[]> {
  const r = await fetch(`${API}/teams?league=${encodeURIComponent(league)}`, { cache: "no-store" });
  if (!r.ok) return [];
  return r.json();
}

export async function getFixtures(league: string) {
  const r = await fetch(`${API}/fixtures?league=${encodeURIComponent(league)}`, { cache: "no-store" });
  if (!r.ok) return [];
  return r.json() as Promise<{ home: string; away: string; date: string }[]>;
}

export type Analysis = {
  stop?: boolean; reason?: string; pick?: string; pickTeam?: string;
  verdict: string; tier?: string; sos?: string; bet?: string;
  odds?: number | null; ev?: number | null; flags?: string[]; phase?: string;
  r?: { z_final: number; comps: any; ppdaValid: boolean; capped: boolean };
  res?: any; managers?: { home: string; away: string }; meta?: any;
};

export async function analyze(body: any): Promise<Analysis> {
  const r = await fetch(`${API}/analyze_by_name`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
