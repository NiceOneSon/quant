-- SCD2 유니버스 히스토리 구간 생성 소스.
-- 실제 편입 구간(is_member=true)만 포함한다.
-- pre-membership/between-gap 행은 제거 — fct_prices에서 편입 전 가격은 null FK 허용.
with memberships as (
    select universe, symbol, added, removed
    from {{ ref('int_universe_membership') }}
)
select
    universe,
    symbol,
    added   as valid_from,
    removed as valid_to,
    true    as is_member
from memberships
