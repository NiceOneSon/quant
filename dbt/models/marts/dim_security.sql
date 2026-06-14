{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_security.parquet')
) }}

-- 종목 마스터: symbol → name, market.
-- sk_id = hash(symbol). symbol 이 실제 어느 종목인지 해석하는 단일 소스.
select
    {{ dbt_utils.generate_surrogate_key(['symbol']) }} as sk_id,
    symbol,
    name,
    market
from {{ ref('stg_securities') }}
