-- Singular test: 유니버스 멤버십 구간 유효성.
-- 실패 조건: valid_to <= valid_from (편출일이 편입일과 같거나 앞선 역전 구간).
-- 정상: valid_to is null (열린 구간) 또는 valid_to > valid_from.
select
    universe,
    symbol,
    valid_from,
    valid_to
from {{ ref('dim_universe_history') }}
where
    valid_to is not null
    and valid_to <= valid_from
