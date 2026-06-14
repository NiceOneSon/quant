-- ELT: Python 은 date/series/value 만 적재.
-- country·label·category 는 fct_macro 에서 macro_series seed 조인으로 파생.
select
    date::DATE   as date,
    series,
    value::DOUBLE as value
from {{ source('raw', 'macro') }}
