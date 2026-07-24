# Yo-Yo AM Line, Challenge 1 Dashboard

Streamlit dashboard of the Simio optimization experiment for the SLS/MJF yo-yo
line: **300 scenarios x 10 replications**, minimizing unit production cost while
keeping every order under a hard 12-hour lead-time promise.

## What's inside

- **Cost vs delivery frontier**: the whole design space as one cost-vs-speed
  trade-off, with the 12 h gate and the recommended configuration.
- **Cost is a printer story**: unit cost vs printer count (about +$1.85/printer),
  plus an LMG variance decomposition of every control (printers explain ~95%).
- **Delivery is a batch story**: worst-case lead time vs batch size, coloured by
  fleet size.
- **The bottleneck**: station utilization and cost composition (capital vs
  pay-per-use); the printer bank is the only real constraint and the only capital.
- **Explore**: sortable table of all 300 designs + CSV download.

## Run locally

```bash
python -m venv .venv                 # use Python 3.10 to 3.13 (NOT 3.9.7)
.venv/Scripts/activate               # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

> Python **3.9.7** is explicitly unsupported by modern Streamlit; use 3.10+.

## Layout

```
app.py               Streamlit app (layout + copy)
charts.py            Plotly figure builders + stats (LMG, Pareto)
theme.py             visual system (MIT-red minimalist palette, CSS)
data/                precomputed datasets the app reads
  scenarios.parquet    300 designs, one row each (means over 10 reps)
  replications.parquet 3000 rows (per-replication responses)
scripts/build_data.py  rebuilds data/ from the raw Simio exports
docs/                  challenge brief + analysis notes (CONTEXT_RESULTS.md)
.streamlit/config.toml theme
Procfile               Railway/Heroku start command
_selftest.py           headless smoke test (streamlit AppTest)
```

## Data provenance

`data/*.parquet` are derived from the raw Simio exports and are committed, so the
app runs and deploys without the raw CSVs.

- **Unit cost** = Simio `TotalCost` response (annualized system cost per saleable
  unit), mean of 10 replications.
- **Lead time** = worst-case order flow time = `max(YoYoBatch time-in-system) +
  max(YoYoBody time-in-system)`, mean of 10 replications. The maximum (not the
  average) is used because the 12 h promise is a hard guarantee.
- **Cost fields**: each object's `CapitalCost + UsageCostCharged + IdleCost` sum
  exactly to its `TotalCost` (verified for all 300 scenarios). Only the AM printer
  bank has a capital cost; every usage cost is billed only while working.

### Rebuilding data (only if the exports change)

Put the two Simio exports (`*ResponseDetail.csv`, `*ResultsDetail.csv`) in a `raw/`
folder at the repo root, then:

```bash
python scripts/build_data.py
```

## Deploy to Railway

Self-contained. Start command (also in `Procfile`):

```
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

Make sure the builder uses Python 3.11+ (3.9.7 is blocked). `requirements.txt` and
`data/*.parquet` are all that is required.
