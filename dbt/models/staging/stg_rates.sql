select
    date,
    series,
    country,
    rate
from {{ source('raw', 'rates') }}
