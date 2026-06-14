{{ config(materialized='view') }}

-- 종목 일간수익률 + KOSPI 수익률 조인.
-- 거래정지일은 ret_1d=null (rolling 계산에서 자동 제외).
-- 멤버십 외 종목은 제외 (is_member_asof 필터).

with stock as (
    select
        date,
        symbol,
        universe,
        close,
        is_halted,
        case
            when is_halted then null
            else close / nullif(lag(close) over (partition by symbol, universe order by date), 0) - 1
        end as ret_1d,
        volume * close as turnover
    from {{ ref('int_prices_pit') }}
    where is_member_asof = true
      and close > 0
),
kospi as (
    select
        f.date,
        f.value / nullif(lag(f.value) over (order by f.date), 0) - 1 as kospi_ret_1d
    from {{ ref('fct_macro') }} f
    join {{ ref('dim_macro_series') }} d on f.sk_dim_macro_series = d.sk_id
    where d.label = 'KOSPI 지수'
)
select
    s.date,
    s.symbol,
    s.universe,
    s.close,
    s.is_halted,
    s.ret_1d,
    s.turnover,
    k.kospi_ret_1d
from stock s
left join kospi k on s.date = k.date
