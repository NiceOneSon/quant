-- 금리 시리즈 + seed(rate_series) 조인 → country·라벨·만기 보강.
-- ELT: country 는 Python 이 아닌 rate_series seed 에서 파생.
select
    r.date,
    r.series,
    coalesce(m.country, 'NA') as country,
    m.label,
    m.tenor,
    r.rate
from {{ ref('stg_rates') }} as r
left join {{ ref('rate_series') }} as m on r.series = m.series
