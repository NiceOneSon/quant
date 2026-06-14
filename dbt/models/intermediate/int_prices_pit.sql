-- 가격(측정값) + point-in-time 유니버스 멤버십 as-of 조인.
-- is_member_asof: 그 거래일에 그 유니버스 멤버였는지(생존편향 검증·필터).
-- _membership_added: 편입일(fct_prices 에서 sk_dim_universe_history 해시 계산용, 소비자 비노출).
select
    p.universe,
    p.symbol,
    p.date,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume,
    p.close_raw,
    p.is_halted,
    (m.symbol is not null) as is_member_asof,
    m.added                as _membership_added
from {{ ref('stg_prices') }} as p
left join {{ ref('stg_universe') }} as m
    on  p.universe = m.universe
    and p.symbol   = m.symbol
    and p.date >= m.added
    and (m.removed is null or p.date < m.removed)
