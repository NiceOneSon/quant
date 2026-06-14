select
    universe,
    symbol,
    added,
    removed
from {{ source('raw', 'universe') }}
