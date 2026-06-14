{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_rates.parquet')
) }}

-- 금리 측정값. label/tenor/country 는 dim_rate_series(sk_dim_rate_series) 에서 조인.
select
    {{ dbt_utils.generate_surrogate_key(['series']) }} as sk_dim_rate_series,
    date,
    rate
from {{ ref('int_rates_enriched') }}
