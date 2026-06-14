-- 금리 시리즈 + seed(rate_series) 조인 → 라벨·만기 보강.
select
    r.date,
    r.series,
    r.country,
    m.label,
    m.tenor,
    r.rate
from {{ ref('stg_rates') }} as r
left join {{ ref('rate_series') }} as m on r.series = m.series
