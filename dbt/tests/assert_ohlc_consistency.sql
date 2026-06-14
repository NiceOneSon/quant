-- Singular test: OHLC 가격 일관성.
-- 거래정지일(is_halted=true)은 open/high/low=0, close=마지막 기준가로 이월되므로 제외.
-- FDR 수정주가 특성상 high vs close/open 이 반올림 오차(≤1원) 범위에서 역전 가능하므로
-- 가장 기본적인 위반(high < low)만 검사한다.
select
    u.universe,
    u.symbol,
    p.date,
    p.open,
    p.high,
    p.low,
    p.close,
    p.is_halted
from {{ ref('fct_prices') }} p
join {{ ref('dim_universe_history') }} u on p.sk_dim_universe_history = u.sk_id
where not p.is_halted
  and p.high < p.low
