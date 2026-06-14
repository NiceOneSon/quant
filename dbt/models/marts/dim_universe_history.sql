{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_universe_history.parquet')
) }}

-- SCD2 유니버스 히스토리 차원.
-- 멤버십 구간(is_member=true)과 갭 구간(is_member=false)으로 전체 날짜 범위를 빈틈없이 커버.
-- fct_prices.sk_dim_universe_history 가 범위 조인(valid_from ≤ date < valid_to)으로 참조 — null FK 없음.
with base as (
    select
        universe,
        symbol,
        valid_from,
        valid_to,
        is_member,
        cast(valid_from as varchar) as _valid_from_str
    from {{ ref('int_universe_history') }}
),
with_sk as (
    select
        {{ dbt_utils.generate_surrogate_key(['universe', 'symbol', '_valid_from_str']) }} as sk_id,
        universe,
        symbol,
        valid_from,
        valid_to,
        is_member,
        (is_member and valid_to is null) as is_current
    from base
)
select
    w.sk_id,
    w.universe,
    w.symbol,
    s.name,
    w.valid_from,
    w.valid_to,
    w.is_member,
    w.is_current
from with_sk w
left join {{ ref('dim_security') }} s on w.symbol = s.symbol
order by w.universe, w.symbol, w.valid_from
