-- 원본 가격 parquet 의 얇은 정리 레이어. (향후 정규화 로직을 Python 에서 이리로 이전)
select
    universe,
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume,
    close_raw,
    is_halted
from {{ source('raw', 'prices') }}
