{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_universe.parquet')
) }}

-- PIT 유니버스 멤버십 구간.
-- sk_id = hash(universe, symbol, added): 각 편입 구간을 고유하게 식별.
-- [added, removed) 반개구간으로 생존편향을 방지한다.
with base as (
    select *, cast(added as varchar) as _added_str
    from {{ ref('int_universe_membership') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['universe', 'symbol', '_added_str']) }} as sk_id,
    universe,
    symbol,
    added,
    removed,
    is_current
from base
