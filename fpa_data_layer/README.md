# FP&A AI Stack — Data Layer

Phase 2 of the FP&A AI Stack. Takes the Forecasting Agent's output
(`../Forecasting_Agent/*_drivers.json` + `*_forecast_output.json`) and turns it
into a refreshable, tested, dashboarded pipeline.

## Pipeline

```
SEC filings (20-F/6-K, 8-K/10-Q)
  -> Python driver extraction        (Forecasting_Agent/*_drivers.json)
  -> Python forecast engine          (Forecasting_Agent/run_forecast.py)
  -> load_raw.py                     (EL: raw JSON -> DuckDB raw schema)
  -> dbt staging + mart              (T: clean, type, join -> fct_company_forecast)
  -> dashboard.py (Streamlit)        (company selector, forecast chart, driver metrics)
```

## Why DuckDB + dbt

Chosen over a Snowflake free trial (setup friction, 30-day clock) and over
plain SQLite (skips the actual skill gap — dbt/ELT fluency). DuckDB is free,
embedded (no server, no account), and pairs natively with dbt via the
`dbt-duckdb` adapter — a real, increasingly common modern-stack combination.

## Environment note (read before running)

**dbt requires Python 3.11**, not whatever system Python is installed. This
machine's system Python (3.14) is too new for `dbt-core` — a dependency
(`mashumaro`) breaks its type-introspection on 3.14. Fix: dbt runs from an
isolated venv, `dbt_venv/`, built on a pre-installed Python 3.11 (via
Astral/uv). The dashboard itself has no dbt dependency and runs fine on
system Python.

If `dbt_venv/` doesn't exist yet:
```bash
py -3.11 -m venv dbt_venv          # or the direct path to a 3.11 install
./dbt_venv/Scripts/pip.exe install dbt-core dbt-duckdb duckdb
```

## Running it

**1. Load raw data** (run whenever the Forecasting Agent produces new/updated JSON):
```bash
python load_raw.py
```

**2. Run dbt** (from this directory, using the 3.11 venv):
```bash
export DBT_PROFILES_DIR="$(pwd)"          # or set on Windows equivalently
./dbt_venv/Scripts/dbt.exe build           # runs models + all 15 tests
```

**3. Launch the dashboard** (system Python, not the dbt venv):
```bash
streamlit run dashboard.py
```

## Adding a new company

No code changes needed:
1. Copy `Forecasting_Agent/driver_schema_template.json`, fill in real filing data
2. Run `python Forecasting_Agent/run_forecast.py <new_company>_drivers.json`
3. Add the filename to `DRIVER_FILES` in `load_raw.py`
4. Re-run `load_raw.py` then `dbt build`
5. The dashboard's company selector picks it up automatically

## Tests (15, all passing)

`models/schema.yml` — not_null on every key column across all 3 models, a
uniqueness test on `company`, and an `accepted_values` test constraining
`ndr_direction` to `expanding`/`contracting`. Run via `dbt build` or `dbt test`.

## Files

- `load_raw.py` — EL script
- `dbt_project.yml`, `profiles.yml` — dbt config
- `models/staging/stg_drivers.sql`, `models/staging/stg_forecast_quarters.sql` — staging (1:1 with raw, typed/renamed)
- `models/marts/fct_company_forecast.sql` — the dashboard's source table
- `models/schema.yml` — column docs + tests
- `dashboard.py` — Streamlit app
- `warehouse.duckdb` — the DuckDB database file (generated, not hand-edited)
