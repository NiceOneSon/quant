{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_macro.parquet')
) }}

-- 매크로/FX/원자재/지수 측정값. label/unit/country/category 는 dim_macro_series 에서 조인.
select
    {{ dbt_utils.generate_surrogate_key(['series']) }} as sk_dim_macro_series,
    series,
    date,
    value
from {{ ref('stg_macro') }}
