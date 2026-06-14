-- Singular test: 동일 (universe, symbol) 의 멤버십 구간 비중첩.
-- 실패 조건: [A1, R1) 과 [A2, R2) 가 겹침 — A1 < A2 이고 R1 > A2 (또는 R1 is null).
-- 이 테스트 실패 = PIT 데이터에 생존편향 위험 존재.
select
    a.universe,
    a.symbol,
    a.added  as interval_a_added,
    a.removed as interval_a_removed,
    b.added  as interval_b_added,
    b.removed as interval_b_removed
from {{ ref('dim_universe') }} as a
join {{ ref('dim_universe') }} as b
    on  a.universe = b.universe
    and a.symbol   = b.symbol
    and a.added    < b.added        -- b 가 a 이후에 시작
where
    -- a 가 b 시작 이전에 끝나지 않음 → 겹침
    a.removed is null
    or b.added < a.removed
