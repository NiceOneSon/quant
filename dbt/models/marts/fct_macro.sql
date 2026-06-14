{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_macro.parquet')
) }}

-- 매크로/FX/원자재/지수 시계열. macro_series seed 로 메타데이터 보강.
select
    s.date,
    s.series,
    m.label,
    m.unit,
    m.country,
    m.category,
    s.value
from {{ ref('stg_macro') }} as s
left join {{ ref('macro_series') }} as m on s.series = m.series
