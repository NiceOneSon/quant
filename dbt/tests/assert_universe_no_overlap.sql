-- Singular test: 동일 (universe, symbol) 의 멤버십 구간 비중첩.
-- 실패 조건: [A_from, A_to) 과 [B_from, B_to) 가 겹침 — A 가 먼저 시작하고 B 시작 전에 끝나지 않음.
-- 이 테스트 실패 = PIT 데이터에 생존편향 위험 존재.
select
    a.universe,
    a.symbol,
    a.valid_from as interval_a_from,
    a.valid_to   as interval_a_to,
    b.valid_from as interval_b_from,
    b.valid_to   as interval_b_to
from {{ ref('dim_universe_history') }} as a
join {{ ref('dim_universe_history') }} as b
    on  a.universe   = b.universe
    and a.symbol     = b.symbol
    and a.valid_from < b.valid_from
where
    a.valid_to is null
    or b.valid_from < a.valid_to
