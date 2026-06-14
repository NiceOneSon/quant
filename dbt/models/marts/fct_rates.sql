{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/fct_rates.parquet')
) }}

select * from {{ ref('int_rates_enriched') }}
