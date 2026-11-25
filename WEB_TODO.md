# Web updates needed after the Route 9 refactor

`node web/scripts/build-data.mjs` passes against the new outputs. Only one audit constant had to change, in `web/scripts/build-data.mjs`: EJ residents in the legacy CBI hotspots, 42,805 to 42,416 (`rows[0].aadt_station` is still 28,112 because the legacy column is kept). Everything below is narrative or presentation that is now out of date. None of it breaks the build.

## Stale numbers and wording

| File | What is stale | Replace with (source: `outputs/summary_statistics.txt`) |
|---|---|---|
| `src/content/paper-abstract.md` | Worcester-only rho +0.57 and 33 hotspots / 42,805 EJ residents; the "single station" model | Worcester tract rho +0.48 (CI +0.17 to +0.72, n=44); FE slope +$11,243/km; 27 priority hotspots (34,339 EJ residents); legacy CBI hotspots 42,416 |
| `src/components/Hero.tsx` (line ~94), `src/config.ts` (line ~43) | AADT 28,112 and 75% westbound presented as the corridor traffic | Measured AADT 13,461-45,937 (mean 28,373); WB 75% is one station |
| `src/components/Methodology.tsx` (lines ~24, 41-47, 71) | "One count station", `AADT = 28,112`, one decay formula | Nearest-segment MassDOT AADT x exp(-d/300 m); sensitivity d=150 m; join tiers T2/T3 |
| `src/components/Summary.tsx` (lines ~84, 109) | "single measured traffic station", "modelled from one count station" | Measured segment AADT along Route 9; block-group exposure is still modelled |
| `src/components/Explorer.tsx` (lines ~211-232), `AirQuality.tsx` (line ~272) | Figure 1 caption describes old panels A-D and one-station exposure; air text repeats the exposure formula | New Figure 1 panels: A Worcester map, B Shrewsbury, C AADT profile, D Worcester tract scatter, E who lives nearby |
| `src/data/dictionary.ts` | `aadt_station` says "same for every row"; none of the 27 new columns are listed | Copy from `outputs/data_dictionary.md` |
| `src/lib/analysis.ts` (line ~181) | `exposure_index` help text | Nearest-segment AADT x exp(-d/300 m); `legacy_exposure_index` is the old model |

## Figures

- `figure1_income_traffic_ej.png` is regenerated with a different layout (build-data copies it as before). Update the lightbox caption and alt text.
- `figure2_pm25_distribution.png` is now "Appendix Figure A1". The panels are unchanged.
- `figure3_priority_hotspots.png` is new and is not copied by `build-data.mjs`. Add it to the filename list in the `for (const f of [...])` loop in `build-data.mjs`, and to `Resources.tsx` and `LINKS`.
- The Explorer's own Scatter and Map components are separate from the PNG. They still plot block groups. Consider a Worcester-only tract view.

## Optional additions

- New master columns the UI can use: `vulnerability_index`, `vuln_quintile`, `priority_hotspot`, `priority_rank`, `est_households`, `est_hh_within_*`, `nearest_segment_aadt`, `exposure_index_d150`.
- Replace the "cumulative burden hotspots" framing with `priority_hotspot` (traffic-independent), keeping CBI as a labelled secondary view. CBI correlates with distance partly by construction.
- Add `outputs/advisory_brief.md`, `outputs/tract_table_route9.csv` and `outputs/data_dictionary.md` to the Resources downloads.
- `web/public/code/route9_deep_analysis.py` is a verbatim copy. The script now imports `fetch_massdot_traffic_aadt.py`, so copy that file too if the code viewer should be runnable.

## Audit constants that will move when inputs change

`build-data.mjs` hard-codes block-group counts, rho 0.47, slope 10651, band medians, buffer EJ populations and 42416. Those are legacy headlines, reproduced exactly. If the web moves to the new headlines, update the checks to the Worcester-primary values.
