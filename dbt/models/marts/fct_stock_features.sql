{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_stock_features.parquet')
) }}

-- 종목 단면 팩터 mart. grain: (date, symbol, universe).
-- raw 팩터 + CS rank (0~1, 항상 높을수록 좋음) + family/composite score.
-- CS rank: percent_rank() over (partition by date, universe).
-- 낮을수록 좋은 팩터(vol, beta)는 1 - percent_rank() 로 반전.

with raw as (
    select
        f.*,
        s.name
    from {{ ref('int_stock_features') }} f
    join {{ ref('dim_security') }} s on f.symbol = s.symbol
),
ranked as (
    select
        {{ dbt_utils.generate_surrogate_key(['date', 'symbol', 'universe']) }} as sk_id,
        date,
        symbol,
        name,
        universe,
        -- Raw 팩터
        mom_1m, mom_6m, mom_12_1m, rev_1w, hi52w_ratio,
        vol_1m, vol_3m, beta_1y, idio_vol_1m,
        adv_20d, vol_surge,
        -- CS rank: Momentum (높을수록 좋음)
        percent_rank() over (partition by date, universe order by mom_12_1m  nulls last) as mom_12_1m_rank,
        percent_rank() over (partition by date, universe order by mom_6m     nulls last) as mom_6m_rank,
        percent_rank() over (partition by date, universe order by mom_1m     nulls last) as mom_1m_rank,
        percent_rank() over (partition by date, universe order by rev_1w     nulls last) as rev_1w_rank,
        percent_rank() over (partition by date, universe order by hi52w_ratio nulls last) as hi52w_ratio_rank,
        -- CS rank: Low-vol/Risk (낮을수록 좋음 → 반전)
        1 - percent_rank() over (partition by date, universe order by vol_1m     nulls last) as vol_1m_rank,
        1 - percent_rank() over (partition by date, universe order by vol_3m     nulls last) as vol_3m_rank,
        1 - percent_rank() over (partition by date, universe order by beta_1y    nulls last) as beta_1y_rank,
        1 - percent_rank() over (partition by date, universe order by idio_vol_1m nulls last) as idio_vol_rank,
        -- CS rank: Liquidity (높을수록 좋음)
        percent_rank() over (partition by date, universe order by adv_20d   nulls last) as adv_20d_rank,
        percent_rank() over (partition by date, universe order by vol_surge  nulls last) as vol_surge_rank
    from raw
),
scored as (
    select
        r.*,
        -- Family score: rank 단순평균. 모두 [0,1], 높을수록 좋음.
        (mom_12_1m_rank + mom_6m_rank + rev_1w_rank + hi52w_ratio_rank) / 4.0 as score_mom,
        (vol_1m_rank + beta_1y_rank + idio_vol_rank)                   / 3.0 as score_lowvol,
        (adv_20d_rank + vol_surge_rank)                                 / 2.0 as score_liq
    from ranked r
)
select
    sk_id,
    date, symbol, name, universe,
    -- Raw
    mom_1m, mom_6m, mom_12_1m, rev_1w, hi52w_ratio,
    vol_1m, vol_3m, beta_1y, idio_vol_1m,
    adv_20d, vol_surge,
    -- CS rank
    mom_12_1m_rank, mom_6m_rank, mom_1m_rank, rev_1w_rank, hi52w_ratio_rank,
    vol_1m_rank, vol_3m_rank, beta_1y_rank, idio_vol_rank,
    adv_20d_rank, vol_surge_rank,
    -- Score
    score_mom, score_lowvol, score_liq,
    (score_mom + score_lowvol + score_liq) / 3.0 as score_composite
from scored
order by date, universe, score_composite desc nulls last
