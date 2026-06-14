-- ELT: Python 은 date/series/rate 만 적재. country 는 int_rates_enriched 에서 seed 조인으로 파생.
select
    date::DATE    as date,
    series,
    rate::DOUBLE  as rate
from {{ source('raw', 'rates') }}
