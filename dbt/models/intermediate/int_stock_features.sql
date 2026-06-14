{{ config(materialized='view') }}

-- 종목 단면(cross-sectional) 팩터 — raw 값. fct_stock_features 에서 CS rank 추가.
-- 팩터 패밀리: Momentum / Low-vol / Liquidity (가격 기반만, 재무 데이터 미수집).
-- 최소 관측: mom_12_1m 은 252 거래일 필요 → 미충족 시 null.

with base as (
    select * from {{ ref('int_daily_returns') }}
),
windowed as (
    select
        date,
        symbol,
        universe,
        close,
        ret_1d,
        turnover,
        kospi_ret_1d,
        -- 가격 래그 (모멘텀 계산용)
        lag(close, 5)   over w as p5d,
        lag(close, 21)  over w as p1m,
        lag(close, 126) over w as p6m,
        lag(close, 252) over w as p12m,
        -- 52주 최고가 (현재 포함, 252 거래일)
        max(close) over w252 as high_52w,
        -- 변동성
        stddev_pop(ret_1d) over w21  as vol_1m,
        stddev_pop(ret_1d) over w63  as vol_3m,
        -- 베타 (OLS slope: cov(ret, kospi) / var(kospi))
        regr_slope(ret_1d, kospi_ret_1d) over w252 as beta_1y,
        -- idio vol 계산용 분산
        var_pop(ret_1d)          over w21 as var_ret_21d,
        var_pop(kospi_ret_1d)    over w21 as var_kospi_21d,
        -- 유동성
        avg(turnover) over w20 as adv_20d,
        avg(turnover) over w5  as adv_5d
    from base
    window
        w    as (partition by symbol, universe order by date),
        w5   as (partition by symbol, universe order by date rows between 4   preceding and current row),
        w20  as (partition by symbol, universe order by date rows between 19  preceding and current row),
        w21  as (partition by symbol, universe order by date rows between 20  preceding and current row),
        w63  as (partition by symbol, universe order by date rows between 62  preceding and current row),
        w252 as (partition by symbol, universe order by date rows between 251 preceding and current row)
)
select
    date,
    symbol,
    universe,
    -- ── Momentum ──────────────────────────────────────────────
    close / nullif(p1m,  0) - 1        as mom_1m,
    close / nullif(p6m,  0) - 1        as mom_6m,
    p1m   / nullif(p12m, 0) - 1        as mom_12_1m,   -- 표준 모멘텀: 최근 1M 제외
    close / nullif(p5d,  0) - 1        as rev_1w,      -- 단기 반전 (음수 신호)
    close / nullif(high_52w, 0)        as hi52w_ratio, -- 52주 최고가 대비
    -- ── Low-vol / Risk ────────────────────────────────────────
    vol_1m,
    vol_3m,
    beta_1y,
    -- 특이변동성: sqrt(총분산 - β²·시장분산), 음수 방지
    sqrt(greatest(var_ret_21d - beta_1y * beta_1y * var_kospi_21d, 0)) as idio_vol_1m,
    -- ── Liquidity ─────────────────────────────────────────────
    adv_20d,
    adv_5d / nullif(adv_20d, 0) as vol_surge  -- 거래대금 급등 (5d/20d)
from windowed
