-- Singular test: 유니버스 멤버십 구간 유효성.
-- 실패 조건: removed <= added (편출일이 편입일과 같거나 앞선 역전 구간).
-- 정상: removed is null (열린 구간) 또는 removed > added.
select
    universe,
    symbol,
    added,
    removed
from {{ ref('dim_universe') }}
where
    removed is not null
    and removed <= added
