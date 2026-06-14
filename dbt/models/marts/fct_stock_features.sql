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
--   2) CS rank  — 같은 날·같은 유니버스 내 종목 간 상대 순위 (0~1)
--                 항상 "높을수록 유리"로 통일 (낮을수록 좋은 팩터는 반전)
--   3) score    — family(패밀리)별 rank 단순평균 → composite 단순평균
--
-- FK:
--   sk_dim_security         → dim_security         (hash(symbol))
--   sk_dim_universe_history → dim_universe_history  (AS-OF 범위 조인)
--
-- 팩터 패밀리 현황 (가격 기반만 구현, 재무 데이터 수집 후 확장 예정)
--   Momentum : mom_12_1m, mom_6m, mom_1m, rev_1w, hi52w_ratio
--   Low-vol  : vol_1m, vol_3m, beta_1y, idio_vol_1m
--   Liquidity: adv_20d, vol_surge
-- ──────────────────────────────────────────────────────────────────────────────

with raw as (
    select * from {{ ref('int_stock_features') }}
),

universe_hist as (
    -- AS-OF 조인용: 날짜 기준 멤버십 구간 → sk_dim_universe_history 확보
    select sk_id, universe, symbol, valid_from, valid_to
    from {{ ref('dim_universe_history') }}
),

ranked as (
    select
        {{ dbt_utils.generate_surrogate_key(['raw.date', 'raw.symbol', 'raw.universe']) }} as sk_id,
        {{ dbt_utils.generate_surrogate_key(['raw.symbol'])                             }} as sk_dim_security,
        uh.sk_id                                                                            as sk_dim_universe_history,
        raw.date,

        -- ── Raw 팩터 ──────────────────────────────────────────────────────────
        raw.mom_1m, raw.mom_6m, raw.mom_12_1m, raw.rev_1w, raw.hi52w_ratio,
        raw.vol_1m, raw.vol_3m, raw.beta_1y, raw.idio_vol_1m,
        raw.adv_20d, raw.vol_surge,

        -- ── CS rank: Momentum ─────────────────────────────────────────────────
        -- 수익률이 높을수록 유리 → percent_rank 그대로 사용
        -- mom_12_1m: 12-1M 표준 모멘텀 (최근 1개월 제외, 과거 반전 효과 제거)
        -- rev_1w: 단기 반전 시그널 — 직전 1주 수익률이 낮은 종목이 유리
        --         (단기 과매도 반등 효과, 랭크 높을수록 직전 1주 상승이 컸던 종목)
        --         ※ 전략에 따라 반전(1 - rank)으로 쓸 수도 있음, 현재는 모멘텀 방향 유지
        percent_rank() over (partition by raw.date, raw.universe order by raw.mom_12_1m   nulls last) as mom_12_1m_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.mom_6m      nulls last) as mom_6m_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.mom_1m      nulls last) as mom_1m_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.rev_1w      nulls last) as rev_1w_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.hi52w_ratio nulls last) as hi52w_ratio_rank,

        -- ── CS rank: Low-vol / Risk ───────────────────────────────────────────
        -- 변동성·베타가 낮을수록 유리 → 1 - percent_rank 로 반전
        -- idio_vol: 베타 제거 후 잔차 변동성. 낮을수록 종목 고유 리스크 작음
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.vol_1m      nulls last) as vol_1m_rank,
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.vol_3m      nulls last) as vol_3m_rank,
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.beta_1y     nulls last) as beta_1y_rank,
        1 - percent_rank() over (partition by raw.date, raw.universe order by raw.idio_vol_1m nulls last) as idio_vol_rank,

        -- ── CS rank: Liquidity ────────────────────────────────────────────────
        -- 거래대금이 클수록 유리 (실제 체결 가능성, 슬리피지 감소)
        -- vol_surge: 최근 5일 거래대금 / 20일 평균. 급등은 단기 관심 증가 신호
        percent_rank() over (partition by raw.date, raw.universe order by raw.adv_20d    nulls last) as adv_20d_rank,
        percent_rank() over (partition by raw.date, raw.universe order by raw.vol_surge  nulls last) as vol_surge_rank

    from raw
    -- AS-OF 조인: raw 의 date 가 멤버십 구간(valid_from ~ valid_to) 안에 있는 행과 매핑
    left join universe_hist uh
        on  raw.universe = uh.universe
        and raw.symbol   = uh.symbol
        and raw.date     >= uh.valid_from
        and (uh.valid_to is null or raw.date < uh.valid_to)
),

scored as (
    select
        r.*,
        -- ── Family score ──────────────────────────────────────────────────────
        -- 패밀리 내 rank 단순평균. 모두 [0,1], 높을수록 해당 패밀리에서 유리
        -- 추후 가중치 최적화 연구 시 여기를 수정 (현재 equal-weight)
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

    -- Raw 팩터 (단위: 수익률은 소수, 변동성은 일간 표준편차, 거래대금은 KRW)
    mom_1m, mom_6m, mom_12_1m, rev_1w, hi52w_ratio,
    vol_1m, vol_3m, beta_1y, idio_vol_1m,
    adv_20d, vol_surge,

    -- CS rank (0~1, 높을수록 유리)
    mom_12_1m_rank, mom_6m_rank, mom_1m_rank, rev_1w_rank, hi52w_ratio_rank,
    vol_1m_rank, vol_3m_rank, beta_1y_rank, idio_vol_rank,
    adv_20d_rank, vol_surge_rank,

    -- Family / composite score
    score_mom, score_lowvol, score_liq,
    -- composite: 패밀리 score 단순평균. 리밸런싱 시 이 값 기준으로 상위 N종목 선정
    (score_mom + score_lowvol + score_liq) / 3.0 as score_composite

from scored
order by date, sk_dim_universe_history, score_composite desc nulls last
