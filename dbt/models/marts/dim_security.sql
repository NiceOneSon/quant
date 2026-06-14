{{ config(
    materialized='external',
    location=(env_var('QUANT_MARTS_DIR', '../data/marts') ~ '/dim_security.parquet')
) }}

-- 종목 마스터: symbol → name, market. symbol 해석의 단일 소스.
select * from {{ ref('stg_securities') }}
