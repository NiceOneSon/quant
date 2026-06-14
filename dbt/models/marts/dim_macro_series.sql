{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_macro_series.parquet')
) }}

-- 매크로 시리즈 마스터. fct_macro.sk_dim_macro_series 가 참조.
-- sk_id = hash(series).
select
    {{ dbt_utils.generate_surrogate_key(['series']) }} as sk_id,
    series,
    label,
    unit,
    country,
    category,
    source
from {{ ref('macro_series') }}
order by category, series
