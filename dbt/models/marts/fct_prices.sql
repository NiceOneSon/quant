{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_prices.parquet')
) }}

select * from {{ ref('stg_prices') }}
