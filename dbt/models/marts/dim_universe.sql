{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_universe.parquet')
) }}

select * from {{ ref('int_universe_membership') }}
