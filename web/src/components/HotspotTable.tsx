import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ChevronDown, ChevronUp } from "lucide-react";
import { blockGroups, type BlockGroup } from "../data";
import { EJ_COLOR } from "../lib/colors";
import { fmtDist, fmtInt, fmtUsd } from "../lib/format";
import { Bar } from "./ui";

type SortKey = "cbi" | "income" | "distM" | "pop" | "pctMinority" | "pctLep";

const COLS: { key: SortKey; label: string; align?: "right" }[] = [
  { key: "pop", label: "Residents", align: "right" },
  { key: "income", label: "Income", align: "right" },
  { key: "pctMinority", label: "% minority", align: "right" },
  { key: "pctLep", label: "% LEP", align: "right" },
  { key: "distM", label: "Distance", align: "right" },
  { key: "cbi", label: "Burden index" },
];

export function HotspotTable({ onSelect, selectedId }: { onSelect: (id: string | null) => void; selectedId: string | null }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "cbi", dir: -1 });
  const [all, setAll] = useState(false);

  const rows = useMemo(() => {
    const h = blockGroups.filter((b) => b.hotspot);
    return [...h].sort((a: BlockGroup, b: BlockGroup) => {
      const av = a[sort.key] ?? -Infinity;
      const bv = b[sort.key] ?? -Infinity;
      return (av === bv ? 0 : av < bv ? -1 : 1) * sort.dir;
    });
  }, [sort]);
  const shown = all ? rows : rows.slice(0, 10);

  const toggle = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: key === "income" || key === "distM" ? 1 : -1 }));

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-rule p-5">
        <div>
          <h3 className="font-serif text-xl font-semibold text-ink">The {rows.length} corridor hotspots</h3>
          <p className="mt-1 max-w-2xl text-[0.88rem] leading-relaxed text-ink-2">
            Block groups inside the corridor <i>and</i> in the top quintile of the cumulative burden index. Click a row to locate it on the map above.
          </p>
        </div>
        <p className="text-xs text-ink-3">Sorted by {COLS.find((c) => c.key === sort.key)?.label.toLowerCase()}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-[0.84rem]">
          <thead className="bg-paper text-[0.68rem] uppercase tracking-wider text-ink-3">
            <tr>
              <th className="px-4 py-2.5 font-semibold">#</th>
              <th className="px-2 py-2.5 font-semibold">Block group</th>
              <th className="px-2 py-2.5 font-semibold">EJ criteria met</th>
              {COLS.map((c) => (
                <th key={c.key} className={`px-2 py-2.5 font-semibold ${c.align === "right" ? "text-right" : ""}`} aria-sort={sort.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}>
                  <button type="button" onClick={() => toggle(c.key)} className="inline-flex items-center gap-1 uppercase tracking-wider hover:text-ink">
                    {c.label}
                    {sort.key === c.key && (sort.dir === 1 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {shown.map((b, i) => (
              <tr
                key={b.id}
                onClick={() => onSelect(selectedId === b.id ? null : b.id)}
                className={`cursor-pointer transition-colors hover:bg-sky-soft/70 ${selectedId === b.id ? "bg-sky-soft" : ""}`}
              >
                <td className="px-4 py-2.5 text-ink-3 tabular">{i + 1}</td>
                <td className="px-2 py-2.5">
                  <button type="button" className="text-left font-medium text-ink" onClick={(e) => { e.stopPropagation(); onSelect(selectedId === b.id ? null : b.id); }}>
                    Tract {b.tract} · BG {b.bg}
                  </button>
                  <div className="text-[0.7rem] text-ink-3">{b.town}</div>
                </td>
                <td className="px-2 py-2.5">
                  <span className="inline-flex items-center gap-1.5 text-ink-2">
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: EJ_COLOR[b.ejDesc] }} />
                    {b.ejDesc}
                  </span>
                </td>
                <td className="px-2 py-2.5 text-right tabular">{fmtInt(b.pop)}</td>
                <td className="px-2 py-2.5 text-right tabular">{fmtUsd(b.income)}</td>
                <td className="px-2 py-2.5 text-right tabular">{b.pctMinority === null ? "n/a" : `${b.pctMinority.toFixed(0)}%`}</td>
                <td className="px-2 py-2.5 text-right tabular">{b.pctLep === null ? "n/a" : `${b.pctLep.toFixed(0)}%`}</td>
                <td className="px-2 py-2.5 text-right tabular">{fmtDist(b.distM)}</td>
                <td className="px-2 py-2.5 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="w-9 font-semibold text-ink tabular">{b.cbi?.toFixed(1)}</span>
                    <div className="w-24">
                      <Bar value={b.cbi ?? 0} max={100} color="#bd0026" height={6} />
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        onClick={() => setAll((v) => !v)}
        className="flex w-full items-center justify-center gap-1.5 border-t border-rule bg-paper py-3 text-sm font-semibold text-navy-2 hover:bg-sky-soft/60"
      >
        {all ? (
          <>
            Show top 10 <ChevronUp className="h-4 w-4" />
          </>
        ) : (
          <>
            Show all {rows.length} hotspots <ChevronDown className="h-4 w-4" />
          </>
        )}
      </button>
    </div>
  );
}
