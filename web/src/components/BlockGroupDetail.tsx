import { MousePointerClick, Pin } from "lucide-react";
import type { BlockGroup } from "../data";
import { MA_MEDIAN_INCOME } from "../data";
import { EJ_COLOR } from "../lib/colors";
import { fmtDist, fmtInt, fmtPct, fmtUsd } from "../lib/format";
import { Bar, Pill } from "./ui";

function Cell({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[0.68rem] font-medium uppercase tracking-wider text-ink-3">{label}</dt>
      <dd className="truncate text-[0.98rem] font-semibold text-ink tabular">{value}</dd>
      {sub && <dd className="text-[0.7rem] text-ink-3">{sub}</dd>}
    </div>
  );
}

export function BlockGroupDetail({ bg, pinned }: { bg: BlockGroup | null; pinned: boolean }) {
  if (!bg) {
    return (
      <div className="flex min-h-[148px] items-center gap-3 rounded-lg border border-dashed border-rule-2 bg-paper/70 p-4 text-sm text-ink-3">
        <MousePointerClick className="h-5 w-5 shrink-0" aria-hidden />
        <span>Hover or tap a block group on the map or scatter plot to inspect it. Click to pin the selection.</span>
      </div>
    );
  }
  return (
    <div className="min-h-[148px] rounded-lg border border-rule bg-paper/70 p-4" aria-live="polite">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="font-serif text-lg font-semibold leading-tight text-ink">
            {bg.town} · Tract {bg.tract}, Block Group {bg.bg}
          </p>
          <p className="text-[0.72rem] text-ink-3 tabular">GEOID {bg.id}</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {pinned && (
            <Pill>
              <Pin className="h-3 w-3" /> Pinned
            </Pill>
          )}
          {bg.hotspot && (
            <span className="rounded-full bg-ink px-2.5 py-0.5 text-[0.7rem] font-semibold text-white">Burden hotspot</span>
          )}
          <Pill color={EJ_COLOR[bg.ejDesc]}>{bg.ejDesc}</Pill>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
        <Cell label="Distance to Route 9" value={fmtDist(bg.distM)} sub={bg.band} />
        <Cell
          label="Median income (tract)"
          value={fmtUsd(bg.income)}
          sub={bg.income !== null ? `${((100 * bg.income) / MA_MEDIAN_INCOME).toFixed(0)}% of MA median${bg.incomeReliable === false ? " · wide margin" : ""}` : "no estimate"}
        />
        <Cell label="Residents (EJ BGs)" value={fmtInt(bg.pop)} sub={bg.pop === null ? "not in EJ layer" : undefined} />
        <Cell label="% minority · % LEP" value={bg.pctMinority === null ? "n/a" : `${fmtPct(bg.pctMinority)} · ${fmtPct(bg.pctLep)}`} />
        <Cell label="Traffic exposure" value={bg.exposure === null ? "n/a" : fmtInt(bg.exposure)} sub="AADT-equiv. veh/day" />
        <Cell label="EJ criteria met" value={bg.ejCount === null ? "n/a" : `${bg.ejCount} of 3`} />
        <div className="col-span-2">
          <dt className="text-[0.68rem] font-medium uppercase tracking-wider text-ink-3">Cumulative burden index</dt>
          <dd className="flex items-center gap-3">
            <span className="w-12 text-[0.98rem] font-semibold text-ink tabular">{bg.cbi === null ? "n/a" : bg.cbi.toFixed(1)}</span>
            <div className="flex-1">{bg.cbi !== null && <Bar value={bg.cbi} max={100} color="#bd0026" height={8} />}</div>
          </dd>
        </div>
      </dl>
    </div>
  );
}
