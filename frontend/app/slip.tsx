import { type Analysis } from "./lib/api";

function Zbar({ name, val }: { name: string; val: number | null }) {
  const v = val == null ? 0 : Math.max(-3, Math.min(3, val));
  const pct = Math.abs(v) / 3 * 50;
  const left = v >= 0 ? 50 : 50 - pct;
  const col = v >= 0 ? "var(--bet)" : "var(--nobet)";
  return (
    <div className="zrow">
      <span className="zname">{name}</span>
      <span className="track"><span className="center" />
        <span className="fill" style={{ left: `${left}%`, width: `${pct}%`, background: col }} /></span>
      <span className="zval">{val == null ? "n/a" : val.toFixed(2)}</span>
    </div>
  );
}

export default function Slip({ a, home, away }: { a: Analysis; home: string; away: string }) {
  if (a.stop) return (
    <div className="slip">
      <div className="slip-top"><div className="matchup">{home} <span className="vs">v</span> {away}</div></div>
      <div className="band nobet"><div className="word">NO BET</div></div>
      <div className="pad"><div className="flag stop">{a.reason}</div></div>
    </div>
  );
  const vc = a.verdict === "BET" ? "bet" : a.verdict === "MONITOR" ? "monitor" : "nobet";
  const c = a.r?.comps ?? {};
  const evTxt = a.ev == null ? "n/a · no odds" : `${(a.ev * 100).toFixed(1)}%`;
  return (
    <div className="slip">
      <div className="slip-top">
        <div className="matchup">{home} <span className="vs">v</span> {away}</div>
        <div className="metaline">{a.meta?.league} · MW {a.meta?.matchweek} · {a.phase} · sample {a.meta?.sample}/10</div>
      </div>
      <div className={`band ${vc}`}>
        <div className="word">{a.verdict}</div>
        <div className="pickbox">Lean<b>{a.pickTeam}</b>{a.tier} signal</div>
      </div>
      <div className="pad">
        <div className="zbars">
          <Zbar name="xG dev" val={c.z_xgdev ?? null} />
          <Zbar name="Form" val={c.z_form ?? null} />
          <Zbar name="PPDA" val={a.r?.ppdaValid ? (c.z_ppda ?? null) : null} />
          <Zbar name="Composite" val={a.r?.z_final ?? null} />
        </div>
        <dl className="kv">
          <dt>Z composite</dt><dd>{a.r?.z_final.toFixed(3)}</dd>
          <dt>Home / Away</dt><dd>{a.res?.home.z_final.toFixed(2)} / {a.res?.away.z_final.toFixed(2)}</dd>
          <dt>SoS</dt><dd><span className={`tag ${a.sos?.toLowerCase()}`}>{a.sos}</span></dd>
          <dt>Odds</dt><dd>{a.odds ?? "—"}</dd>
        </dl>
        <div className="betline">
          <div className="market">{a.bet}</div>
          <div className={`ev ${a.ev != null && a.ev >= 0 ? "pos" : "neg"}`}>EV: <b>{evTxt}</b></div>
        </div>
        {a.flags && a.flags.length > 0 &&
          <div className="flags">{a.flags.map(f => <div key={f} className="flag">{f}</div>)}</div>}
      </div>
    </div>
  );
}
