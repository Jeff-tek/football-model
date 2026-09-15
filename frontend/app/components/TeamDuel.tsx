import type { Tip } from "../lib/tips";

const num = (v: number | null | undefined): string =>
  typeof v === "number" ? String(v) : "–";

export default function TeamDuel({ t }: { t: Tip }) {
  const h = t.teamMeta?.home;
  const a = t.teamMeta?.away;
  if (!h && !a) return null;
  const rows: [string, string, string][] = [
    ["Rank", num(h?.rank), num(a?.rank)],
    ["Pts", num(h?.points), num(a?.points)],
    ["Played", num(h?.played), num(a?.played)],
    ["W–D–L", `${num(h?.wins)}–${num(h?.draws)}–${num(h?.losses)}`, `${num(a?.wins)}–${num(a?.draws)}–${num(a?.losses)}`],
    ["GF / GA", `${num(h?.gf)} / ${num(h?.ga)}`, `${num(a?.gf)} / ${num(a?.ga)}`],
    ["Form", t.homeForm || "–", t.awayForm || "–"],
    ["xG", t.homeXG.toFixed(2), t.awayXG.toFixed(2)],
  ];
  return (
    <div className="viz-block">
      <div className="viz-title">Team data · this league</div>
      <table className="team-table">
        <thead>
          <tr><th></th><th>{t.home}</th><th>{t.away}</th></tr>
        </thead>
        <tbody>
          {rows.map(([k, hv, av]) => (
            <tr key={k}><td className="team-k">{k}</td><td>{hv}</td><td>{av}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
