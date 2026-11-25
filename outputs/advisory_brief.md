# Route 9 corridor (Worcester and Shrewsbury): advisory brief

Plain-language summary of `outputs/summary_statistics.txt`. Every number below is computed by `route9_deep_analysis.py` and matches that file.

## The short version

- Route 9 carries between 13,461 and 45,937 vehicles a day inside the two towns (average about 28,373), measured by MassDOT segment counts. Traffic is heaviest in Shrewsbury and the eastern end; about 44% of the road carries 30,000 or more.
- Worcester is the main equity story. Households within about a mile of the road have a median income near $56,458, versus $82,432 in the rest of the city; 46% of corridor households earn under $50,000 versus 31%.
- Income rises with distance from Route 9 in Worcester (tract-level correlation +0.48). This holds with town effects included, so it is not just Worcester versus Shrewsbury.
- Close to the road: roughly 47,144 residents of environmental justice (EJ) areas live within 500 m (about 17,275 households in all); 8,633 EJ residents live within 500 m of the busiest (30,000+) stretches, mostly at the Shrewsbury end; Worcester's lower-income corridor neighbourhoods sit beside 14,000-28,000 stretches.
- 27 neighbourhood block groups near the road rank in the most vulnerable fifth by income and EJ criteria alone (no traffic involved); they are the suggested first look.
- Air quality data are county-wide only. They show the region meets the federal annual PM2.5 standard but sits above the stricter WHO guideline; they cannot say anything about Route 9 itself.

## Who lives near the road

| Distance from Route 9 | EJ residents | Households (est.) | Median household income (inside) | Beyond |
|---|---|---|---|---|
| within 300 m (both towns) | 28,786 (13% of EJ residents) | 10,573 (11%) | $56,223 | $80,773 |
| within 500 m (both towns) | 47,144 (22% of EJ residents) | 17,275 (18%) | $58,083 | $82,837 |
| within 1000 m (both towns) | 81,149 (37% of EJ residents) | 31,432 (33%) | $61,703 | $87,071 |

EJ residents are counted only in EJ-designated block groups (the state table has no population for the others), so they undercount, especially in Shrewsbury. Households come from the Census income table and cover every block group.

## Worcester

- 146 block groups, 46 tracts; 70 block groups (25 tracts) are within 1.5 km of Route 9.
- 97% of corridor block groups are EJ-designated versus 88% elsewhere in Worcester (odds ratio 4.6).
- Each extra kilometre from the road goes with roughly +$11,243 higher tract income (95% interval +$6,609 to +$15,876, town effects included).
- The map and tract table (`outputs/tract_table_route9.csv`) show which tracts are closest, poorest and busiest.

## Shrewsbury (check, not the headline)

- Few corridor block groups (11), high incomes (tract median $134,585); treating the two towns together barely changes the pattern (tract-level correlation +0.41 vs +0.48 for Worcester alone).

## Where to look first

Block groups in the top vulnerability fifth (low income plus EJ criteria) within 1.5 km of Route 9 (Figure 3):

| Rank | Tract-block group | Town | Tract income | EJ residents within 500 m | Adjacent AADT |
|---|---|---|---|---|---|
| 1 | 7312.03-3 | Worcester | $26,054 | 1,675 | 19,161 |
| 2 | 7316.02-2 | Worcester | $26,458 | 1,970 | 16,373 |
| 3 | 7318.02-2 | Worcester | $36,560 | 1,500 | 27,636 |
| 4 | 7318.02-4 | Worcester | $36,560 | 539 | 24,430 |
| 5 | 7314-1 | Worcester | $41,667 | 0 | 19,924 |
| 6 | 7314-2 | Worcester | $41,667 | 0 | 19,701 |
| 7 | 7313-2 | Worcester | $43,025 | 0 | 19,161 |
| 8 | 7318.01-2 | Worcester | $50,602 | 978 | 20,565 |

In total 27 block groups meet the test (34,339 EJ residents). A 0 in the 500 m column means no part of that block group's area lies within 500 m of the road; the block group is still inside the 1.5 km corridor.

## What this does not tell us

- Traffic next to homes is modelled by distance from the road, not measured. Only the volume on Route 9 itself is measured.
- Nothing here measures pollution at the roadside, health effects, or cause and effect.
- The westbound-heavy count at one station (75% westbound) is not a corridor-wide fact.
- PM2.5: 2025 mean 5.65 ug/m3 at two county monitors about 23 km apart; no monitor sits on Route 9.

## Suggested next steps

1. Commission near-road PM2.5 / NO2 (or UFP) monitoring on the >= 30k stretches and beside priority block groups; ambient county monitors cannot answer the corridor question.
2. Ask MassDOT for classification counts with truck share and directional volumes at M3002W-class stations to verify the westbound skew and refresh older (pre-2023) segments.
3. Treat Worcester as the primary equity case; review the priority block-group list (Figure 3, tract table) with neighbourhood groups before any targeting decision.
4. Fill the population gap (decennial / ACS block-group population for non-EJ block groups) so near-road counts cover everyone, not only EJ-designated residents.
5. Pair this analysis with tract health outcomes (e.g., asthma ED visits) if the group wants evidence on effects rather than proximity.
6. Re-run annually (fetch_massdot_traffic_aadt.py --refresh) as MassDOT updates AADT vintages.

## Sources

MassDOT Roads services (RoadInventoryLRS Traffic, Traffic_Station; TrafficCountLocations); ACS 5-year 2024 table S1901; MassGIS 2020 Environmental Justice block groups; US Census TIGER/Line 2024; EPA Air Quality System. Re-run: `python fetch_massdot_traffic_aadt.py` then `python route9_deep_analysis.py`.
