-- SCD2 유니버스 히스토리 구간 생성 소스.
-- 세 가지 구간 유형을 합쳐 (universe, symbol) 쌍의 전체 타임라인을 빈틈없이 커버한다.
-- dim_universe_history 와 fct_prices 가 이 모델을 소비한다.
with memberships as (
    select universe, symbol, added, removed
    from {{ ref('int_universe_membership') }}
),

-- (1) 멤버십 구간: 실제 유니버스 편입 기간.
member_intervals as (
    select
        universe,
        symbol,
        added      as valid_from,
        removed    as valid_to,
        true       as is_member
    from memberships
),

-- (2) 편입 전 갭: 가격 데이터가 첫 편입일보다 앞선 종목을 커버.
--    valid_from = epoch sentinel(1900-01-01) → 수집 시작일이 언제든 항상 포함.
--    valid_to   = 해당 (universe, symbol)의 최초 편입일.
--    현재 데이터: 40종목이 2021-01-04(가격 시작) ~ 2023-06-01(첫 편입) 갭 보유.
pre_membership_gaps as (
    select
        universe,
        symbol,
        cast('1900-01-01' as date) as valid_from,
        min(added)                 as valid_to,
        false                      as is_member
    from memberships
    group by universe, symbol
),

-- (3) 재편입 갭: removed 후 다음 added 사이 공백.
--    현재 데이터에는 0건이나 미래 재편입 케이스를 위해 포함.
between_gaps as (
    select
        universe,
        symbol,
        removed as valid_from,
        lead(added) over (
            partition by universe, symbol
            order by added
        ) as valid_to,
        false as is_member
    from memberships
    where removed is not null
    qualify lead(added) over (
        partition by universe, symbol
        order by added
    ) is not null
)

select universe, symbol, valid_from, valid_to, is_member from member_intervals
union all
select universe, symbol, valid_from, valid_to, is_member from pre_membership_gaps
union all
select universe, symbol, valid_from, valid_to, is_member from between_gaps
