{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_rate_series.parquet')
) }}

-- 금리 시리즈 마스터. fct_rates.sk_dim_rate_series 가 참조.
-- sk_id = hash(series).
select
    {{ dbt_utils.generate_surrogate_key(['series']) }} as sk_id,
    series,
    country,
    label,
    tenor
from {{ ref('rate_series') }}
