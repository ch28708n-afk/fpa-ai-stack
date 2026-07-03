-- Staging: one row per company per forecasted quarter, plus a computed
-- band width (high - low) for the dashboard's confidence visualization.

select
    company,
    quarter,
    -- quarters come out of the Python engine as "Q_ YYYY" strings; split into
    -- sortable parts so the dashboard/marts can order chronologically.
    cast(substr(quarter, 2, 1) as integer) as quarter_num,
    cast(substr(quarter, 4, 4) as integer) as fiscal_year,
    low_musd,
    base_case_musd,
    high_musd,
    round(high_musd - low_musd, 1) as band_width_musd
from raw.forecast_quarters
