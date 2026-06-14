-- 가격(측정값) + point-in-time 유니버스 멤버십 플래그(as-of 조인).
-- 정규화: 종목명(name) 등 속성은 fact 에 넣지 않고 dim_security 에서 symbol 로 조인한다.
-- is_member_asof: 그 거래일에 그 유니버스 멤버였는지(생존편향 검증·필터).
-- 멤버십 구간은 비중첩(검증)이라 최대 1건만 매칭 → fan-out 없음.
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
    (m.symbol is not null) as is_member_asof
from {{ ref('stg_prices') }} as p
left join {{ ref('int_universe_membership') }} as m
    on p.universe = m.universe
    and p.symbol = m.symbol
    and p.date >= m.added
    and (m.removed is null or p.date < m.removed)
