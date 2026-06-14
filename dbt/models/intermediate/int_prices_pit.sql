-- 가격 × point-in-time 유니버스 멤버십(as-of 조인).
-- 해당 거래일에 그 유니버스 멤버였는지(is_member_asof)를 플래그 → 생존편향 검증·필터용.
-- 멤버십 구간은 비중첩(normalize 에서 강제)이라 최대 1건만 매칭 → fan-out 없음.
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
