# Data dictionary: `outputs/master_route9_table.csv`

166 block groups x 89 columns. Legacy columns keep their names and positions; new columns are appended after `hotspot`. Columns marked MODELLED are not measurements.

Changed meaning: `exposure_index` (now measured segment AADT x decay; old model in `legacy_exposure_index`). `aadt_station` / `aadt_westbound` / `aadt_eastbound` / `westbound_share` are the M3002W anchor, not corridor loading.

| Column | Description |
|---|---|
| `geoid_bg` | Census block-group GEOID (12 digits). |
| `geoid_tract` | Census tract GEOID (11 digits). |
| `bg_name` | MassGIS block-group name (EJ block groups only). |
| `municipality` | Worcester or Shrewsbury. |
| `ej_designated` | Block group present in MassGIS EJ_POLY (EJ-designated). |
| `ej_criteria_code` | MassGIS EJ criteria code. |
| `ej_criteria_count` | EJ criteria met (0-3; 0 = not EJ). |
| `ej_criteria_desc` | EJ criteria met, text. |
| `ej_income` | EJ criterion: median household income <= 65% of state. |
| `ej_minority` | EJ criterion: minority share. |
| `ej_english_isolation` | EJ criterion: English isolation. |
| `total_pop` | Block-group population (EJ_POLY; blank for non-EJ block groups). |
| `total_hh` | Households (EJ_POLY; blank for non-EJ). |
| `pct_minority` | % minority (EJ block groups only). |
| `lep_hh` | Limited-English households (EJ only). |
| `pct_lep_hh` | % limited-English households (EJ only). |
| `bg_median_hh_income` | Block-group median household income, EJ table (older ACS vintage). |
| `acs_median_income` | ACS 2024 5-yr tract median household income (repeated for each block group in the tract). |
| `acs_median_income_moe` | Margin of error of acs_median_income. |
| `acs_income_cv` | Coefficient of variation of acs_median_income. |
| `acs_income_reliable` | True when CV < 0.30. |
| `acs_income_topcoded` | Tract median is top-coded. |
| `acs_pct_hh_under_50k` | % households under $50,000 (tract). |
| `acs_pct_hh_150k_plus` | % households at or above $150,000 (tract). |
| `income_best` | acs_median_income, else EJ-table income. |
| `income_source` | Where income_best came from. |
| `income_pct_of_state` | income_best as % of the statewide median. |
| `centroid_lat` | Block-group centroid latitude. |
| `centroid_lon` | Block-group centroid longitude. |
| `area_km2` | Block-group land+water polygon area (km2). |
| `dist_centroid_m` | Distance, block-group centroid to TIGER Route 9 centreline (m). Primary distance. |
| `dist_edge_m` | Distance, nearest polygon edge to Route 9 (m). |
| `mean_dist_m` | Mean distance over the block group's 50 m grid cells (m). |
| `dist_band` | Band of dist_centroid_m. |
| `in_corridor` | dist_centroid_m <= 1,500 m. |
| `exposure_index` | MODELLED. Nearest MassDOT Route 9 segment AADT x exp(-d/300 m), mean over 50 m grid cells (AADT-equivalent veh/day). Replaces the single-station model. |
| `pct_area_within_300m` | % of block-group area within 300 m of Route 9. |
| `pct_area_within_500m` | % of area within 500 m. |
| `pct_area_within_1000m` | % of area within 1 km. |
| `pm_monitor` | Nearest EPA PM2.5 monitor (label only; regional context). |
| `dist_pm_monitor_km` | Distance to that monitor (km). |
| `pm25_monitor_annual_mean` | That monitor's mean daily PM2.5 (ug/m3). |
| `pm25_monitor_p98` | 98th percentile daily PM2.5. |
| `pm25_monitor_max` | Maximum daily PM2.5. |
| `pm25_monitor_days_over_who24` | Days above WHO 24-h guideline (15 ug/m3). |
| `shape_area` | EJ_POLY polygon area (source units). |
| `shape_len` | EJ_POLY polygon perimeter (source units). |
| `acs_households` | ACS tract households (S1901). |
| `acs_mean_income` | ACS tract mean household income. |
| `aadt_station` | traffic.csv anchor AADT at M3002W (same for every row; NOT corridor loading). |
| `aadt_westbound` | Anchor westbound AADT at M3002W. |
| `aadt_eastbound` | Anchor eastbound AADT at M3002W. |
| `westbound_share` | Anchor westbound share at M3002W (single station). |
| `est_ej_pop_within_300m` | EJ residents within 300 m (areal interpolation). |
| `est_ej_pop_within_500m` | EJ residents within 500 m. |
| `est_ej_pop_within_1000m` | EJ residents within 1 km. |
| `p_traffic` | Percentile rank of exposure_index (0-1). |
| `p_low_income` | Percentile rank of low income. |
| `p_ej_criteria` | Percentile rank of EJ criteria count. |
| `cumulative_burden_index` | Legacy CBI 0-100: mean of p_traffic, p_low_income, p_ej_criteria. Distance link is partly by construction. |
| `cbi_quintile` | Quintile of CBI. |
| `hotspot` | Legacy: top CBI quintile AND in_corridor. |
| `exposure_index_d150` | Sensitivity: as exposure_index with 150 m decay. |
| `legacy_exposure_index` | Previous release model: 28,112 x exp(-d/300 m), mean over grid. Kept one release. |
| `pct_area_within_300m_aadt20k` | % of area within 300 m of Route 9 where the adjacent segment AADT >= 20,000. |
| `pct_area_within_300m_aadt30k` | ... >= 30,000. |
| `pct_area_within_500m_aadt20k` | % within 500 m, adjacent AADT >= 20,000. |
| `pct_area_within_500m_aadt30k` | ... >= 30,000. |
| `pct_area_within_1000m_aadt20k` | % within 1 km, adjacent AADT >= 20,000. |
| `pct_area_within_1000m_aadt30k` | ... >= 30,000. |
| `nearest_segment_id` | MassDOT LRS Traffic segment nearest the centroid (route@milepost). |
| `nearest_segment_aadt` | MEASURED AADT of that segment (veh/day). |
| `nearest_segment_aadt_year` | AADT_Year of that segment. |
| `exposure_method` | Model used for the row (segment_nearest_lrs_aadt_d300 or fallback). |
| `nearest_station_id` | Nearest on-Route-9 count station with AADT (or M3002W anchor). |
| `nearest_station_aadt` | AADT joined to that station. |
| `nearest_station_aadt_year` | AADT_Year of that station's segment. |
| `nearest_station_dist_m` | Distance centroid to that station (m). |
| `est_ej_pop_within_300m_aadt30k` | EJ residents within 300 m of segments >= 30,000 AADT. |
| `est_ej_pop_within_500m_aadt30k` | ... within 500 m. |
| `est_ej_pop_within_1000m_aadt30k` | ... within 1 km. |
| `est_households` | Estimated households: ACS tract households allocated across block groups (EJ-table households as shares). |
| `est_hh_within_300m` | Estimated households within 300 m. |
| `est_hh_within_500m` | Estimated households within 500 m. |
| `est_hh_within_1000m` | Estimated households within 1 km. |
| `vulnerability_index` | Traffic-independent 0-100: mean percentile of low income and EJ criteria. |
| `vuln_quintile` | Quintile of vulnerability_index. |
| `priority_hotspot` | vuln_quintile = Q5 AND in_corridor. |
| `priority_rank` | Rank among priority hotspots (vulnerability, then EJ residents within 500 m). |

## Other outputs

- `outputs/tract_table_route9.csv`: one row per tract (income, distance, adjacent AADT, EJ counts, vulnerability).
- `cache/massdot/*.geojson`: raw MassDOT pulls (re-run `fetch_massdot_traffic_aadt.py --refresh` to update).
