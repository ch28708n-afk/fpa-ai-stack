-- Staging: one row per company, drivers as typed columns, growth rates as
-- readable percentages. Sits directly on raw.drivers — no business logic here,
-- just cleaning/renaming (per dbt convention: staging = 1:1 with source).

select
    company,
    as_of_quarter,
    round(revenue_growth_trailing_avg * 100, 2)  as revenue_growth_trailing_pct,
    round(revenue_growth_guidance_lo * 100, 2)   as revenue_growth_guidance_lo_pct,
    round(revenue_growth_guidance_hi * 100, 2)   as revenue_growth_guidance_hi_pct,
    round(ndr_overall * 100, 1)                  as ndr_overall_pct,
    round(ndr_enterprise_100k_plus * 100, 1)     as ndr_enterprise_pct,
    round((ndr_enterprise_100k_plus - ndr_overall) * 100, 2) as ndr_spread_pp,
    round(gross_margin * 100, 1)                 as gross_margin_pct,
    customers_100k_plus,
    round(customers_100k_plus_yoy_growth * 100, 1) as customers_100k_plus_yoy_pct,
    total_rpo_musd,
    round(total_rpo_yoy_growth * 100, 1)         as total_rpo_yoy_pct,
    deferred_revenue_musd,
    round(deferred_revenue_yoy_growth * 100, 1)  as deferred_revenue_yoy_pct,
    round(non_gaap_op_margin_prior_fy * 100, 1)  as non_gaap_op_margin_prior_fy_pct,
    known_gaps_count,
    case
        when ndr_overall >= 1.0 then 'expanding'
        else 'contracting'
    end as ndr_direction
from raw.drivers
