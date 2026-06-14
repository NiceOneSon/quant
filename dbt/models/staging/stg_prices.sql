-- ELT: Python 은 raw OHLCV 를 적재(is_halted 없음). is_halted 는 여기서 파생.
select
    universe,
    symbol,
    date::DATE                    as date,
    open::DOUBLE                  as open,
    high::DOUBLE                  as high,
    low::DOUBLE                   as low,
    close::DOUBLE                 as close,
    volume::BIGINT                as volume,
    close_raw::DOUBLE             as close_raw,
    (volume = 0)                  as is_halted
from {{ source('raw', 'prices') }}
