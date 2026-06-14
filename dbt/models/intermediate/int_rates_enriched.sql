-- 정규화 후: label/tenor/country 는 dim_rate_series(seed) 가 보유.
-- fct_rates 는 순수 측정값(date, series, rate) + sk_dim_rate_series 만 갖는다.
select
    date,
    series,
    rate
from {{ ref('stg_rates') }}
