{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_prices.parquet')
) }}

-- 일별 수정주가 OHLCV.
-- sk_dim_security         → dim_security (symbol 기준).
-- sk_dim_universe_history → dim_universe_history (범위 조인, 항상 non-null).
--   멤버십 구간(is_member=true): 편입 기간 행.
--   갭 구간(is_member=false) : 편입 전·재편입 공백 기간 행.
with base as (
    select *
    from {{ ref('int_prices_pit') }}
),
universe_hist as (
    select sk_id, universe, symbol, valid_from, valid_to
    from {{ ref('dim_universe_history') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['base.date', 'base.universe', 'base.symbol']) }} as sk_id,
    {{ dbt_utils.generate_surrogate_key(['base.symbol'])                               }} as sk_dim_security,
    uh.sk_id                                                                               as sk_dim_universe_history,
    base.universe,
    base.symbol,
    base.date,
    base.open,
    base.high,
    base.low,
    base.close,
    base.volume,
    base.close_raw,
    base.is_halted,
    base.is_member_asof
from base
join universe_hist uh
    on  base.universe = uh.universe
    and base.symbol   = uh.symbol
    and base.date     >= uh.valid_from
    and (uh.valid_to is null or base.date < uh.valid_to)
order by base.universe, base.symbol, base.date
