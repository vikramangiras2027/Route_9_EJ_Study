# Spatial equity along the Route 9 corridor (Worcester & Shrewsbury, MA)

Independent environmental justice study by **Vikram Angiras** (Shrewsbury High School). The project maps **measured** MassDOT traffic along Route 9, describes **who lives nearby** using Census and MassGIS Environmental Justice data, and places **regional** PM₂.₅ monitors in context. Results are **neighborhood-level associations**, not roadside pollution measurements, health outcomes, or proof of causation.

**Interactive site (GitHub Pages):** [https://vikramangiras2027.github.io/Route_9_EJ_Study/](https://vikramangiras2027.github.io/Route_9_EJ_Study/)

## Repository contents

| Path | Description |
| --- | --- |
| [`route9_deep_analysis.py`](route9_deep_analysis.py) | Main analysis pipeline (tables, figures, `summary_statistics.txt`) |
| [`fetch_massdot_traffic_aadt.py`](fetch_massdot_traffic_aadt.py) | Downloads and caches MassDOT segment AADT and count stations |
| [`outputs/`](outputs/) | Master CSV, tract table, data dictionary, narrative statistics |
| [`charts/`](charts/) | Figure 1–3 (PNG) |
| [`web/`](web/) | React data explorer, paper PDF, and deploy workflow for GitHub Pages |

## Reproduce the analysis

You need local copies of the study inputs (ACS table S1901, MassGIS `EJ_POLY.dbf`, MassDOT anchor `traffic.csv`, EPA PM₂.₅ export). Place them in a folder and either pass it as an argument or set `ROUTE9_DATA_DIR`.

```bash
pip install numpy pandas geopandas scipy matplotlib dbfread

python fetch_massdot_traffic_aadt.py    # fills ./cache/massdot/
python route9_deep_analysis.py /path/to/data-folder

cd web && npm install && npm run build    # audits CSV vs report, builds the site
```

The web app ships with precomputed `geometry.json` and `blockgroups.json`, so `npm run build` works without the TIGER cache after clone.

## Data sources

MassDOT Roads GIS (LRS traffic, count locations), MassGIS 2020 Environmental Justice populations, U.S. Census ACS 2024 (S1901) and TIGER/Line 2024, U.S. EPA Air Quality System (Worcester County PM₂.₅, 2025). See [`web/src/config.ts`](web/src/config.ts) (`SOURCES`) and the paper PDF on the site for citations and limitations.

## License

Analysis code may be reused with attribution. Third-party data remain subject to their providers’ terms. Add a root `LICENSE` file before fork/redistribution if you need explicit terms.