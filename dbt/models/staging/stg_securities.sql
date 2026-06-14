select
    symbol,
    name,
    market
from {{ source('raw', 'securities') }}
