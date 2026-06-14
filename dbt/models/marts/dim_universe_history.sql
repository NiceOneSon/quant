{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_universe_history.parquet')
) }}

-- 유니버스 멤버십 이력 차원. int_universe_history(valid_from/valid_to) 에서 생성.
-- valid_to=null 이면 현재 편입 중. fct_prices.sk_dim_universe_history → 범위 조인.
with with_sk as (
    select
        {{ dbt_utils.generate_surrogate_key(['universe', 'symbol', 'added']) }} as sk_id,
        universe,
        symbol,
        added   as valid_from,
        removed as valid_to,
        (removed is null) as is_current
    from {{ ref('stg_universe') }}
)
select
    w.sk_id,
    w.universe,
    w.symbol,
    s.name,
    w.valid_from,
    w.valid_to,
    w.is_current
from with_sk w
left join {{ ref('dim_security') }} s on w.symbol = s.symbol
order by w.sk_id
