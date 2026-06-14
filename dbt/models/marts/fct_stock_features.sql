{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_stock_features.parquet')
) }}

-- 종목 단면 팩터 mart. grain: (date, symbol, universe).
-- raw 팩터 + CS rank (0~1, 항상 높을수록 좋음) + family/composite score.
-- sk_dim_security         → dim_security
-- sk_dim_universe_history → dim_universe_history (AS-OF 범위 조인)
-- fct 에 자연키(symbol, universe)·메타(name) 없음 — dim 참조로만.

with raw as (
    select * from {{ ref('int_stock_features') }}
),
universe_hist as (
    select sk_id, universe, symbol, valid_from, valid_to
    from {{ ref('dim_universe_history') }}
),
ranked as (
    select
        {{ dbt_utils.generate_surrogate_key(['raw.date', 'raw.symbol', 'raw.universe']) }} as sk_id,
        {{ dbt_utils.generate_surrogate_key(['raw.symbol'])                             }} as sk_dim_security,
        uh.sk_id                                                                            as sk_dim_universe_history,
        raw.date,
        -- Raw 팩터
        raw.mom_1m, raw.mom_6m, raw.mom_12_1m, raw.rev_1w, raw.hi52w_ratio,
        raw.vol_1m, raw.vol_3m, raw.beta_1y, raw.idio_vol_1m,
        raw.adv_20d, raw.vol_surge,
        -- CS rank: Momentum (높을수록 좋음)
        percent_rank() over (partition by raw.date, raw.universe order by raw.mom_12_1m   nulls last) as mom_12_1m_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.mom_6m      nulls last) as mom_6m_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.mom_1m      nulls last) as mom_1m_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.rev_1w      nulls last) as rev_1w_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.hi52w_ratio nulls last) as hi52w_ratio_rank,
        -- CS rank: Low-vol/Risk (낮을수록 좋음 → 반전)
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.vol_1m      nulls last) as vol_1m_rank,
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.vol_3m      nulls last) as vol_3m_rank,
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.beta_1y     nulls last) as beta_1y_rank,
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.idio_vol_1m nulls last) as idio_vol_rank,
        -- CS rank: Liquidity (높을수록 좋음)
        percent_rank() over (partition by raw.date, raw.universe order by raw.adv_20d    nulls last) as adv_20d_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.vol_surge  nulls last) as vol_surge_rank
    from raw
    left join universe_hist uh
        on  raw.universe = uh.universe
        and raw.symbol   = uh.symbol
        and raw.date     >= uh.valid_from
        and (uh.valid_to is null or raw.date < uh.valid_to)
),
scored as (
    select
        r.*,
        (mom_12_1m_rank + mom_6m_rank + rev_1w_rank + hi52w_ratio_rank) / 4.0 as score_mom,
        (vol_1m_rank + beta_1y_rank + idio_vol_rank)                    / 3.0 as score_lowvol,
        (adv_20d_rank + vol_surge_rank)                                  / 2.0 as score_liq
    from ranked r
)
select
    sk_id,
    sk_dim_security,
    sk_dim_universe_history,
    date,
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
order by date, sk_dim_universe_history, score_composite desc nulls last
