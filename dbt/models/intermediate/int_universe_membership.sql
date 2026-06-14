-- 유니버스 멤버십 구간(키만) + 파생(현재 편입 여부).
-- name 같은 종목 속성은 dim_security 에만 둔다(정규화) → 필요 시 symbol 로 조인.
select
    universe,
    symbol,
    added,
    removed,
    (removed is null) as is_current
from {{ ref('stg_universe') }}
