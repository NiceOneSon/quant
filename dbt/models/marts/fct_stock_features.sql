{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_stock_features.parquet')
) }}

-- ──────────────────────────────────────────────────────────────────────────────
-- fct_stock_features: 종목 단면(cross-sectional) 팩터 mart
-- grain: (date, symbol, universe) — 날짜 × 종목 × 유니버스별 1행
--
-- 목적: 롱온리 랭킹 바스켓 구성을 위한 팩터 스코어 계산
--   1) raw 팩터 — int_stock_features 에서 계산된 rolling 윈도우 값
--   2) winsorized — 같은 날·유니버스 내 p1/p99 clip (극단값 rank 오염 방지)
--   3) CS rank  — winsorized 값 기준 상대 순위 (0~1)
--                 항상 "높을수록 유리"로 통일 (낮을수록 좋은 팩터는 반전)
--   4) score    — family(패밀리)별 rank 단순평균 → composite 단순평균
--
-- FK:
--   sk_dim_security         → dim_security         (hash(symbol))
--   sk_dim_universe_history → dim_universe_history  (AS-OF 범위 조인)
--
-- 팩터 패밀리 현황 (가격 기반만 구현, 재무 데이터 수집 후 확장 예정)
--   Momentum : mom_12_1m, mom_6m, mom_1m, rev_1w, hi52w_ratio
--   Low-vol  : vol_1m, vol_3m, beta_1y, idio_vol_1m
--   Liquidity: adv_20d (log), vol_surge
-- ──────────────────────────────────────────────────────────────────────────────

with raw as (
    select * from {{ ref('int_stock_features') }}
),

universe_hist as (
    -- AS-OF 조인용: 날짜 기준 멤버십 구간 → sk_dim_universe_history 확보
    select sk_id, universe, symbol, valid_from, valid_to
    from {{ ref('dim_universe_history') }}
),

-- winsorize 경계값: date × universe 별 p1/p99 집계 후 raw 에 조인
-- percentile_cont 는 ordered-set aggregate 로 window function 미지원 → 별도 CTE 분리
bounds as (
    select
        date, universe,
        -- Momentum
        percentile_cont(0.01) within group (order by mom_12_1m)          as mom_12_1m_p01,
        percentile_cont(0.99) within group (order by mom_12_1m)          as mom_12_1m_p99,
        percentile_cont(0.01) within group (order by mom_6m)             as mom_6m_p01,
        percentile_cont(0.99) within group (order by mom_6m)             as mom_6m_p99,
        percentile_cont(0.01) within group (order by mom_1m)             as mom_1m_p01,
        percentile_cont(0.99) within group (order by mom_1m)             as mom_1m_p99,
        percentile_cont(0.01) within group (order by rev_1w)             as rev_1w_p01,
        percentile_cont(0.99) within group (order by rev_1w)             as rev_1w_p99,
        -- Low-vol
        percentile_cont(0.01) within group (order by vol_1m)             as vol_1m_p01,
        percentile_cont(0.99) within group (order by vol_1m)             as vol_1m_p99,
        percentile_cont(0.01) within group (order by vol_3m)             as vol_3m_p01,
        percentile_cont(0.99) within group (order by vol_3m)             as vol_3m_p99,
        percentile_cont(0.01) within group (order by beta_1y)            as beta_1y_p01,
        percentile_cont(0.99) within group (order by beta_1y)            as beta_1y_p99,
        percentile_cont(0.01) within group (order by idio_vol_1m)        as idio_vol_1m_p01,
        percentile_cont(0.99) within group (order by idio_vol_1m)        as idio_vol_1m_p99,
        -- Liquidity: adv_20d log 변환 기준
        percentile_cont(0.01) within group (order by ln(nullif(adv_20d, 0))) as adv_log_p01,
        percentile_cont(0.99) within group (order by ln(nullif(adv_20d, 0))) as adv_log_p99,
        percentile_cont(0.01) within group (order by vol_surge)          as vol_surge_p01,
        percentile_cont(0.99) within group (order by vol_surge)          as vol_surge_p99
    from raw
    group by date, universe
),

winsorized as (
    select
        r.*,
        greatest(b.mom_12_1m_p01, least(b.mom_12_1m_p99, r.mom_12_1m)) as w_mom_12_1m,
        greatest(b.mom_6m_p01,    least(b.mom_6m_p99,    r.mom_6m))    as w_mom_6m,
        greatest(b.mom_1m_p01,    least(b.mom_1m_p99,    r.mom_1m))    as w_mom_1m,
        greatest(b.rev_1w_p01,    least(b.rev_1w_p99,    r.rev_1w))    as w_rev_1w,
        r.hi52w_ratio                                                    as w_hi52w_ratio,
        greatest(b.vol_1m_p01,    least(b.vol_1m_p99,    r.vol_1m))    as w_vol_1m,
        greatest(b.vol_3m_p01,    least(b.vol_3m_p99,    r.vol_3m))    as w_vol_3m,
        greatest(b.beta_1y_p01,   least(b.beta_1y_p99,   r.beta_1y))   as w_beta_1y,
        greatest(b.idio_vol_1m_p01, least(b.idio_vol_1m_p99, r.idio_vol_1m)) as w_idio_vol_1m,
        greatest(b.adv_log_p01,   least(b.adv_log_p99,   ln(nullif(r.adv_20d, 0)))) as w_adv_20d_log,
        greatest(b.vol_surge_p01, least(b.vol_surge_p99, r.vol_surge))  as w_vol_surge
    from raw r
    join bounds b on r.date = b.date and r.universe = b.universe
),

ranked as (
    select
        {{ dbt_utils.generate_surrogate_key(['w.date', 'w.symbol', 'w.universe']) }} as sk_id,
        {{ dbt_utils.generate_surrogate_key(['w.symbol'])                          }} as sk_dim_security,
        uh.sk_id                                                                       as sk_dim_universe_history,
        w.date,

        -- ── Raw 팩터 (원본 보존) ──────────────────────────────────────────────
        w.mom_1m, w.mom_6m, w.mom_12_1m, w.rev_1w, w.hi52w_ratio,
        w.vol_1m, w.vol_3m, w.beta_1y, w.idio_vol_1m,
        w.adv_20d, w.vol_surge,

        -- ── CS rank: Momentum (winsorized 기준) ──────────────────────────────
        -- 수익률이 높을수록 유리 → percent_rank 그대로 사용
        -- mom_12_1m: 12-1M 표준 모멘텀 (최근 1개월 제외, 과거 반전 효과 제거)
        -- rev_1w: 단기 반전 시그널 — 직전 1주 수익률이 낮은 종목이 유리
        --         ※ 전략에 따라 반전(1 - rank)으로 쓸 수도 있음, 현재는 모멘텀 방향 유지
        percent_rank() over (partition by w.date, w.universe order by w_mom_12_1m   nulls last) as mom_12_1m_rank,
        percent_rank() over (partition by w.date, w.universe order by w_mom_6m      nulls last) as mom_6m_rank,
        percent_rank() over (partition by w.date, w.universe order by w_mom_1m      nulls last) as mom_1m_rank,
        percent_rank() over (partition by w.date, w.universe order by w_rev_1w      nulls last) as rev_1w_rank,
        percent_rank() over (partition by w.date, w.universe order by w_hi52w_ratio nulls last) as hi52w_ratio_rank,

        -- ── CS rank: Low-vol / Risk (낮을수록 유리 → 반전) ──────────────────
        -- idio_vol: 베타 제거 후 잔차 변동성. 낮을수록 종목 고유 리스크 작음
        1 - percent_rank() over (partition by w.date, w.universe order by w_vol_1m      nulls last) as vol_1m_rank,
        1 - percent_rank() over (partition by w.date, w.universe order by w_vol_3m      nulls last) as vol_3m_rank,
        1 - percent_rank() over (partition by w.date, w.universe order by w_beta_1y     nulls last) as beta_1y_rank,
        1 - percent_rank() over (partition by w.date, w.universe order by w_idio_vol_1m nulls last) as idio_vol_rank,

        -- ── CS rank: Liquidity ────────────────────────────────────────────────
        -- adv_20d: log 변환 후 rank (분포 왜도 완화)
        -- vol_surge: 최근 5일 거래대금 / 20일 평균. 급등은 단기 관심 증가 신호
        percent_rank() over (partition by w.date, w.universe order by w_adv_20d_log nulls last) as adv_20d_rank,
        percent_rank() over (partition by w.date, w.universe order by w_vol_surge   nulls last) as vol_surge_rank

    from winsorized w
    -- AS-OF 조인: raw 의 date 가 멤버십 구간(valid_from ~ valid_to) 안에 있는 행과 매핑
    left join universe_hist uh
        on  w.universe = uh.universe
        and w.symbol   = uh.symbol
        and w.date     >= uh.valid_from
        and (uh.valid_to is null or w.date < uh.valid_to)
),

scored as (
    select
        r.*,
        -- ── Family score ──────────────────────────────────────────────────────
        -- 패밀리 내 rank 단순평균. 모두 [0,1], 높을수록 해당 패밀리에서 유리
        -- 추후 가중치 최적화 연구 시 여기를 수정 (현재 equal-weight)
        (mom_12_1m_rank + mom_6m_rank + rev_1w_rank + hi52w_ratio_rank) / 4.0 as score_mom,
        -- beta_1y 는 lowvol 패밀리에서 제외:
        --   beta는 시장 노출도(market risk)로 모멘텀과 구조적으로 높은 역상관(-0.88)을 가져
        --   lowvol 패밀리에 포함 시 composite 에서 모멘텀 신호를 과도하게 상쇄함.
        --   idio_vol(종목 고유 리스크)·vol 만으로 lowvol 구성, beta_1y_rank 는 참조용으로만 보존.
        (vol_1m_rank + idio_vol_rank)                                    / 2.0 as score_lowvol,
        (adv_20d_rank + vol_surge_rank)                                  / 2.0 as score_liq
    from ranked r
)

select
    sk_id,
    sk_dim_security,
    sk_dim_universe_history,
    date,

    -- Raw 팩터 (단위: 수익률은 소수, 변동성은 일간 표준편차, 거래대금은 KRW)
    mom_1m, mom_6m, mom_12_1m, rev_1w, hi52w_ratio,
    vol_1m, vol_3m, beta_1y, idio_vol_1m,
    adv_20d, vol_surge,

    -- CS rank (0~1, 높을수록 유리, winsorized 값 기준)
    mom_12_1m_rank, mom_6m_rank, mom_1m_rank, rev_1w_rank, hi52w_ratio_rank,
    vol_1m_rank, vol_3m_rank, beta_1y_rank, idio_vol_rank,
    adv_20d_rank, vol_surge_rank,

    -- Family / composite score
    score_mom, score_lowvol, score_liq,
    -- composite: 패밀리 score 단순평균. 리밸런싱 시 이 값 기준으로 상위 N종목 선정
    (score_mom + score_lowvol + score_liq) / 3.0 as score_composite

from scored
order by date, sk_dim_universe_history, score_composite desc nulls last
