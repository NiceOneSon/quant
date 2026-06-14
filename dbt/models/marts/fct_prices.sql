{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_prices.parquet')
) }}

select * from {{ ref('int_prices_pit') }}
