-- dbt 마트 fct_rates (소비 레이어). label/tenor 포함.
select * from read_parquet('../../data/marts/fct_rates.parquet')
