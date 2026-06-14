-- 유니버스 멤버십 구간 + 파생(현재 편입 여부).
select
    universe,
    symbol,
    added,
    removed,
    (removed is null) as is_current
from {{ ref('stg_universe') }}
