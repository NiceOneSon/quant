{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_universe.parquet')
) }}

select * from {{ ref('stg_universe') }}
