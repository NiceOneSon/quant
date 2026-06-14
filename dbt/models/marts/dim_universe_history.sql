{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_universe_history.parquet')
) }}

-- SCD2 유니버스 히스토리 차원.
-- 멤버십 구간(is_member=true)과 갭 구간(is_member=false)으로 전체 날짜 범위를 빈틈없이 커버.
-- fct_prices.sk_dim_universe_history 가 이 테이블을 범위 조인(valid_from ≤ date < valid_to)으로 참조.
-- dim_universe: 실제 편입 구간 전용 (기존 유지).
-- dim_universe_history: 전체 타임라인 커버 — null FK 제거를 위한 SCD2 확장.
with base as (
    select
        universe,
        symbol,
        valid_from,
        valid_to,
        is_member,
        cast(valid_from as varchar) as _valid_from_str
    from {{ ref('int_universe_history') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['universe', 'symbol', '_valid_from_str']) }} as sk_id,
    universe,
    symbol,
    valid_from,
    valid_to,
    is_member,
    (is_member and valid_to is null) as is_current
from base
order by universe, symbol, valid_from
