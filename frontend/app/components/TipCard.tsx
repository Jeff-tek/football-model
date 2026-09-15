import type { Tip } from "../lib/tips";
import { OddsRadar, CrowdBars } from "./ModelVisuals";

const pct = (p: number): string => `${(p * 100).toFixed(0)}%`;

export const fmtDate = (iso: string): string => {
  if (!iso) return "TBD";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 16).replace("T", " ");
  return d.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function TipCard({ t }: { t: Tip }) {
  const vc =
    t.verdict === "BET" ? "bet" : t.verdict === "MARGINAL" ? "marginal" : "nobet";
  const edgePos = t.edge.value > 0;
  const [ph, pd, pa] = t.probs["1X2"];
  const [fh, fd, fa] = t.fair["1X2"];
  const [dc1x, dc12, dcx2] = t.probs.DC ?? [0, 0, 0];
  return (
    <article className="tip-card">
      <div className="tip-top">
        <div className="tip-matchup">
          {t.home} <span className="vs">v</span> {t.away}
        </div>
        <div className="tip-meta">
          <span>{fmtDate(t.date)}</span>
          {t.homeForm && (
            <span>
              Form {t.homeForm} · {t.awayForm}
            </span>
          )}
          <span>
            xG {t.homeXG.toFixed(2)} – {t.awayXG.toFixed(2)}
          </span>
          {t.models && t.models.length > 1 && (
            <span>Models: {t.models.join(" + ")}</span>
          )}
        </div>
      </div>
      <div className={`tip-band ${vc}`}>
        <div className="word">{t.verdict}</div>
        <div className="tip-pickbox">
          Pick<b>{t.pick}</b>
          <span className={`edge-badge ${edgePos ? "pos" : "neg"}`}>
            {edgePos ? `+${(t.edge.value * 100).toFixed(1)}%` : "no edge"}
          </span>
        </div>
      </div>
      <div className="tip-body">
        <div className="prob-grid">
          <div className="prob-cell">
            <div className="prob-label">1</div>
            <div className="prob-val">
              {pct(ph)} <small>fair {pct(fh)}</small>
            </div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">X</div>
            <div className="prob-val">
              {pct(pd)} <small>fair {pct(fd)}</small>
            </div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">2</div>
            <div className="prob-val">
              {pct(pa)} <small>fair {pct(fa)}</small>
            </div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">O2.5</div>
            <div className="prob-val">{pct(t.probs["O2.5"])}</div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">U2.5</div>
            <div className="prob-val">{pct(t.probs["U2.5"] ?? 1 - t.probs["O2.5"])}</div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">BTTS</div>
            <div className="prob-val">{pct(t.probs.BTTS)}</div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">1X</div>
            <div className="prob-val">{pct(dc1x)}</div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">12</div>
            <div className="prob-val">{pct(dc12)}</div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">X2</div>
            <div className="prob-val">{pct(dcx2)}</div>
          </div>
          <div className="prob-cell">
            <div className="prob-label">Confidence</div>
            <div className="prob-val">{t.confidence.toFixed(0)}%</div>
          </div>
        </div>
        {t.lineMove && (
          <div className="steam-line steam-own">
            Steam:{" "}
            {["Home", "Draw", "Away"]
              .filter((k) => t.lineMove?.[k as keyof typeof t.lineMove])
              .map((k) => `${k} ${t.lineMove?.[k as keyof typeof t.lineMove]}`)
              .join(" · ")}
          </div>
        )}
        <div className="viz-grid">
          <OddsRadar t={t} />
          <CrowdBars t={t} />
        </div>
        <div className="tip-reasons">
          {t.reasons.map((r) => (
            <div key={r} className="tip-reason">
              {r}
            </div>
          ))}
        </div>
        {t.crowd?.url && (
          <div className="crowd-link-row">
            <a className="source-link" href={t.crowd.url} target="_blank" rel="noreferrer">
              Crowd market ↗
            </a>
          </div>
        )}
        <div className="source-links">
          {t.sources.map((s) => (
            <a
              key={s.name}
              className="source-link"
              href={s.url}
              target="_blank"
              rel="noreferrer"
            >
              {s.name}
            </a>
          ))}
        </div>
      </div>
    </article>
  );
}
