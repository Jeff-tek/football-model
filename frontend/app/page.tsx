"use client";
import { useEffect, useState } from "react";
import { getTeams, getFixtures, getUpcoming, analyze, type Analysis } from "./lib/api";
import Slip from "./slip";

const LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga",
  "Ligue 1", "Russian Premier League"];
const GK = [["first_choice_top5", "First choice · top-5"],
  ["first_choice_avg", "First choice · avg"], ["backup", "Backup"],
  ["emergency", "Emergency"]];

export default function Home() {
  const [league, setLeague] = useState(LEAGUES[0]);
  const [teams, setTeams] = useState<string[]>([]);
  const [fixtures, setFixtures] = useState<{home:string;away:string;date:string}[]>([]);
  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const [homeGk, setHomeGk] = useState("first_choice_avg");
  const [awayGk, setAwayGk] = useState("first_choice_avg");
  const [rivalry, setRivalry] = useState(false);
  const [res, setRes] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    getTeams(league).then(setTeams);
    getFixtures(league).then(fxs => {
      if (fxs.length) { setFixtures(fxs); return; }
      getUpcoming(league).then(uxs => setFixtures(
        uxs.map(u => ({ home: u.home, away: u.away, date: "" }))
      ));
    });
    setHome(""); setAway(""); setRes(null);
  }, [league]);

  async function run() {
    if (!home || !away) return;
    setLoading(true); setErr(""); setRes(null);
    try {
      setRes(await analyze({
        league,
        home,
        away,
        overrides: { rivalry },
        home_gk: homeGk !== "first_choice_avg" ? homeGk : undefined,
        away_gk: awayGk !== "first_choice_avg" ? awayGk : undefined,
      }));
    } catch (e: any) { setErr(e.message ?? "failed"); }
    finally { setLoading(false); }
  }

  return (
    <main className="wrap">
      <header className="masthead">
        <div>
          <div className="kicker">EV-First Decision Engine · v2.2</div>
          <h1 className="title">The Model Desk</h1>
        </div>
        <p className="sub">Pick a fixture. Live data feeds the gates, composite Z, and EV check.</p>
      </header>

      <div className="grid2">
        <section>
          <div className="eyebrow"><span className="num">01</span> Fixture</div>
          <label className="f">League
            <select value={league} onChange={e => setLeague(e.target.value)}>
              {LEAGUES.map(l => <option key={l}>{l}</option>)}
            </select>
          </label>

          {fixtures.length > 0 && (
            <label className="f">Upcoming
              <select onChange={e => { const f = fixtures[+e.target.value];
                if (f) { setHome(f.home); setAway(f.away); } }}>
                <option>Pick a scheduled match…</option>
                  {fixtures.map((f, i) => (
                    <option key={i} value={i}>{f.home} v {f.away}{f.date ? ` — ${f.date.slice(0,10)}` : ""}</option>
                  ))}
              </select>
            </label>
          )}

          <div className="row">
            <label className="f">Home
              <select value={home} onChange={e => setHome(e.target.value)}>
                <option value="">Select…</option>
                {teams.map(t => <option key={t}>{t}</option>)}
              </select></label>
            <label className="f">Away
              <select value={away} onChange={e => setAway(e.target.value)}>
                <option value="">Select…</option>
                {teams.map(t => <option key={t}>{t}</option>)}
              </select></label>
          </div>
          <div className="row">
            <label className="f">Home GK
              <select value={homeGk} onChange={e => setHomeGk(e.target.value)}>
                {GK.map(g => <option key={g[0]} value={g[0]}>{g[1]}</option>)}</select></label>
            <label className="f">Away GK
              <select value={awayGk} onChange={e => setAwayGk(e.target.value)}>
                {GK.map(g => <option key={g[0]} value={g[0]}>{g[1]}</option>)}</select></label>
          </div>
          <label className="f check">
            <input type="checkbox" checked={rivalry} onChange={e => setRivalry(e.target.checked)} />
            Rivalry / derby
          </label>

          <button className="run" onClick={run} disabled={loading || !home || !away}>
            {loading ? "Analyzing…" : "Run analysis"}
          </button>
          {err && <p className="err">{err}</p>}
        </section>

        <section className="results">
          <div className="eyebrow"><span className="num">02</span> Verdict</div>
          {res ? <Slip a={res} home={home} away={away} />
               : <div className="empty">Pick a fixture and run it. The verdict lands here.</div>}
        </section>
      </div>
    </main>
  );
}
