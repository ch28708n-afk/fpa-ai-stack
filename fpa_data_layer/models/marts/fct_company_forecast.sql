-- Mart: the dashboard's single source table. One row per company per
-- forecasted quarter, joined against that company's driver context, with a
-- sequential quarter index (1-8) for clean charting regardless of each
-- company's actual fiscal calendar.

with ordered_quarters as (
    select
        *,
        row_number() over (
            partition by company
            order by fiscal_year, quarter_num
        ) as quarter_index
    from {{ ref('stg_forecast_quarters') }}
)

select
    f.company,
    f.quarter,
    f.quarter_index,
    f.low_musd,
    f.base_case_musd,
    f.high_musd,
    f.band_width_musd,
    d.as_of_quarter as base_quarter,
    d.revenue_growth_trailing_pct,
    d.ndr_overall_pct,
    d.ndr_direction,
    d.ndr_spread_pp,
    d.gross_margin_pct,
    d.total_rpo_yoy_pct,
    d.known_gaps_count
from ordered_quarters f
left join {{ ref('stg_drivers') }} d
    on f.company = d.company
order by f.company, f.quarter_index
