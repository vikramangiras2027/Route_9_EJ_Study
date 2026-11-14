import { Callout, Section } from "./ui";

/**
 * All values below are transcribed from outputs/summary_statistics.txt (section 3).
 * Bootstrap CIs are tract-cluster bootstrap 95% intervals.
 */
const FOREST = [
  { label: "Distance ↔ income", sub: "all block groups, n = 164", rho: 0.47, lo: 0.197, hi: 0.662, p: "<0.001" },
  { label: "Distance ↔ income", sub: "Worcester only, n = 144", rho: 0.568, lo: 0.29, hi: 0.74, p: "<0.001" },
  { label: "Distance ↔ income", sub: "Shrewsbury only, n = 20", rho: 0.641, lo: 0.02, hi: 0.88, p: "0.002" },
  { label: "Distance ↔ EJ-designated", sub: "all block groups, n = 166", rho: -0.19, lo: -0.318, hi: -0.06, p: "0.014" },
];

const CORRIDOR_TESTS = [
  { metric: "Tract median income", a: "$52,011", b: "$84,407", delta: "−0.44", p: "<0.001" },
  { metric: "% households under $50k", a: "44.6%", b: "31.3%", delta: "+0.44", p: "<0.001" },
  { metric: "EJ criteria met (0–3)", a: "2", b: "1", delta: "+0.32", p: "<0.001" },
  { metric: "% minority (EJ block groups)", a: "57.6%", b: "44.4%", delta: "+0.22", p: "0.021" },
  { metric: "% LEP households (EJ block groups)", a: "10.4%", b: "6.4%", delta: "+0.22", p: "0.020" },
  { metric: "Block-group income, EJ table", a: "$44,465", b: "$60,048", delta: "−0.19", p: "0.050" },
  { metric: "Cumulative burden index*", a: "69.3", b: "33.9", delta: "+0.74", p: "<0.001" },
];

const DISTANCE_ROBUSTNESS = [
  { measure: "Centroid distance (primary)", inc: "+0.470", ej: "−0.190 (0.014)", crit: "−0.342" },
  { measure: "Polygon-edge distance", inc: "+0.290", ej: "−0.133 (0.088)", crit: "−0.207" },
  { measure: "Area-weighted mean distance", inc: "+0.475", ej: "−0.194 (0.012)", crit: "−0.347" },
  { measure: "Modelled traffic exposure", inc: "−0.417", ej: "+0.173 (0.026)", crit: "+0.295" },
];

const SENSITIVITY = [
  { r: "≤ 500 m", n: 32, inEj: "100.0", outEj: "87.3", inInc: "$41,667", outInc: "$81,949", gap: "−$40,282" },
  { r: "≤ 1,000 m", n: 61, inEj: "98.4", outEj: "84.8", inInc: "$50,602", outInc: "$84,407", gap: "−$33,805" },
  { r: "≤ 1,500 m (primary)", n: 81, inEj: "96.3", outEj: "83.5", inInc: "$52,011", outInc: "$84,407", gap: "−$32,396" },
  { r: "≤ 2,000 m", n: 98, inEj: "92.9", outEj: "85.3", inInc: "$61,522", outInc: "$84,407", gap: "−$22,885" },
  { r: "≤ 3,000 m", n: 129, inEj: "90.7", outEj: "86.5", inInc: "$67,168", outInc: "$105,571", gap: "−$38,403" },
];

function Forest() {
  const W = 640;
  const L = 250;
  const R = 70;
  const lo = -0.5;
  const hi = 1;
  const x = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  const rowH = 52;
  const H = FOREST.length * rowH + 52;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="Forest plot of Spearman correlations with 95% bootstrap confidence intervals. Distance versus income is positive in all three samples; distance versus EJ designation is negative.">
      <g fontFamily="Inter Variable, sans-serif">
        {[-0.5, 0, 0.5, 1].map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={6} y2={H - 34} stroke={t === 0 ? "#0f1b2d" : "#e6e2d8"} strokeWidth={t === 0 ? 1.5 : 1} />
            <text x={x(t)} y={H - 18} textAnchor="middle" fontSize={11} fill="#667085">
              {t > 0 ? `+${t.toFixed(1)}` : t < 0 ? `−${Math.abs(t).toFixed(1)}` : "0"}
            </text>
          </g>
        ))}
        <text x={x(-0.25)} y={H - 2} textAnchor="middle" fontSize={10.5} fill="#667085">
          ← less with distance
        </text>
        <text x={x(0.6)} y={H - 2} textAnchor="middle" fontSize={10.5} fill="#667085">
          more with distance →
        </text>
        {FOREST.map((f, i) => {
          const y = 28 + i * rowH;
          const neg = f.rho < 0;
          const c = neg ? "#b45309" : "#1d3a6b";
          return (
            <g key={f.label + f.sub}>
              <text x={0} y={y - 2} fontSize={13} fontWeight={600} fill="#0f1b2d">
                {f.label}
              </text>
              <text x={0} y={y + 14} fontSize={11} fill="#667085">
                {f.sub}
              </text>
              <line x1={x(f.lo)} x2={x(f.hi)} y1={y} y2={y} stroke={c} strokeWidth={3} strokeLinecap="round" />
              <circle cx={x(f.rho)} cy={y} r={6.5} fill={c} stroke="#fff" strokeWidth={2} />
              <text x={W} y={y + 4} textAnchor="end" fontSize={12.5} fontWeight={700} fill="#0f1b2d">
                {f.rho > 0 ? "+" : "−"}
                {Math.abs(f.rho).toFixed(2)}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

const th = "px-3 py-2.5 text-[0.68rem] font-semibold uppercase tracking-wider text-ink-3";
const td = "px-3 py-2.5 tabular";

export function Evidence() {
  return (
    <Section
      id="evidence"
      eyebrow="Statistical evidence"
      title="How robust are the patterns?"
      tone="white"
      intro={
        <>
          Spatial data violate the independence assumptions of textbook tests (nearby block groups resemble each other; Moran&rsquo;s I for log income = <b>0.73</b>). The headline intervals therefore use a{" "}
          <b>tract-cluster bootstrap</b>, and effect sizes are reported alongside p-values.
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="card p-5 sm:p-6 lg:col-span-7">
          <h3 className="font-serif text-xl font-semibold text-ink">Spearman correlations with 95% confidence intervals</h3>
          <p className="mb-4 mt-1 text-[0.88rem] leading-relaxed text-ink-2">
            Income rises with distance in every sample, including <i>within</i> each town separately, which rules out the simple Worcester-vs-Shrewsbury explanation. The EJ-designation association is smaller but its interval excludes zero.
          </p>
          <Forest />
          <p className="mt-3 text-[0.75rem] leading-snug text-ink-3">
            Points: Spearman &rho;; bars: tract-cluster bootstrap 95% CI. Worcester-only OLS slope: +$10,926 per km (R&sup2; = 0.28); all block groups: +$10,651 per km (R&sup2; = 0.16). Tract-level (n = 52): &rho; = +0.41, p = 0.003.
          </p>
        </div>

        <div className="card overflow-hidden lg:col-span-5">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3">
            <h3 className="font-serif text-xl font-semibold text-ink">Does the choice of distance matter?</h3>
            <p className="mt-1 text-[0.88rem] leading-relaxed text-ink-2">Spearman &rho; of each proximity measure with each outcome (p-value in brackets where not &lt; 0.001).</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-[0.82rem]">
              <thead className="bg-paper">
                <tr>
                  <th className={th}>Measure</th>
                  <th className={th}>Income</th>
                  <th className={th}>EJ-designated</th>
                  <th className={th}>EJ criteria</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {DISTANCE_ROBUSTNESS.map((r) => (
                  <tr key={r.measure}>
                    <td className="px-3 py-2.5 font-medium text-ink">{r.measure}</td>
                    <td className={td}>{r.inc}</td>
                    <td className={td}>{r.ej}</td>
                    <td className={td}>{r.crit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-5 py-3 text-[0.75rem] leading-snug text-ink-3 sm:px-6">
            Direction is stable. Using nearest polygon-edge distance weakens (and for EJ designation loses significance) the association, so the EJ result should be read as suggestive, not definitive.
          </p>
        </div>

        <div className="card overflow-hidden lg:col-span-7">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3">
            <h3 className="font-serif text-xl font-semibold text-ink">Corridor vs. rest of Worcester &amp; Shrewsbury</h3>
            <p className="mt-1 text-[0.88rem] leading-relaxed text-ink-2">
              Medians compared with Mann-Whitney U; <b>Cliff&rsquo;s &delta;</b> is the effect size (0 = none, &plusmn;1 = complete separation).
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-[0.84rem]">
              <thead className="bg-paper">
                <tr>
                  <th className={th}>Metric (median)</th>
                  <th className={th}>Corridor</th>
                  <th className={th}>Elsewhere</th>
                  <th className={th}>Cliff&rsquo;s &delta;</th>
                  <th className={th}>p</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {CORRIDOR_TESTS.map((r) => (
                  <tr key={r.metric}>
                    <td className="px-3 py-2.5 font-medium text-ink">{r.metric}</td>
                    <td className={td}>{r.a}</td>
                    <td className={td}>{r.b}</td>
                    <td className={td}>{r.delta}</td>
                    <td className={td}>{r.p}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-5 py-3 text-[0.75rem] leading-snug text-ink-3 sm:px-6">
            *The burden index includes modelled traffic exposure, which is a function of distance, so its corridor contrast is partly by construction.
          </p>
        </div>

        <div className="card overflow-hidden lg:col-span-5">
          <div className="p-5 pb-3 sm:p-6 sm:pb-3">
            <h3 className="font-serif text-xl font-semibold text-ink">Sensitivity to the corridor definition</h3>
            <p className="mt-1 text-[0.88rem] leading-relaxed text-ink-2">Income gap is negative and p &lt; 0.001 at every radius.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[440px] text-left text-[0.8rem]">
              <thead className="bg-paper">
                <tr>
                  <th className={th}>Corridor</th>
                  <th className={th}>BGs</th>
                  <th className={th}>% EJ in / out</th>
                  <th className={th}>Income gap</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {SENSITIVITY.map((r) => (
                  <tr key={r.r} className={r.r.includes("primary") ? "bg-sky-soft/70 font-medium" : ""}>
                    <td className="px-3 py-2.5 text-ink">{r.r}</td>
                    <td className={td}>{r.n}</td>
                    <td className={td}>
                      {r.inEj} / {r.outEj}
                    </td>
                    <td className={td}>{r.gap}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-5 py-3 text-[0.75rem] leading-snug text-ink-3 sm:px-6">Interactive version: use the slider in the corridor explorer.</p>
        </div>
      </div>

      <div className="mt-6">
        <Callout title="Interpretation guardrails">
          These are <b>ecological</b> associations between neighborhoods and one road. Block-group incomes are the parent tract&rsquo;s ACS estimate (six tracts have coefficients of variation above 30%), demographics exist only for EJ-designated block groups, and p-values that ignore spatial dependence are
          naive. The cluster-bootstrap intervals are the safer guide.
        </Callout>
      </div>
    </Section>
  );
}
