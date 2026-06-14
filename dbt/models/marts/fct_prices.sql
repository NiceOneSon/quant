{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_prices.parquet')
) }}

-- 일별 수정주가 OHLCV.
-- sk_dim_security: dim_security.sk_id 참조 (symbol 로 조인).
-- sk_dim_universe: dim_universe.sk_id 참조 (편입 구간 기준); 비편입 행은 null.
with base as (
    select *, cast(_membership_added as varchar) as _added_str
    from {{ ref('int_prices_pit') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['date', 'universe', 'symbol'])               }} as sk_id,
    {{ dbt_utils.generate_surrogate_key(['symbol'])                                   }} as sk_dim_security,
    case when _membership_added is not null
        then {{ dbt_utils.generate_surrogate_key(['universe', 'symbol', '_added_str']) }}
        else null
    end                                                                                   as sk_dim_universe,
    universe,
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume,
    close_raw,
    is_halted,
    is_member_asof
from base
order by universe, symbol, date
