-- dbt 마트 fct_macro (소비 레이어). label/unit/country/category 포함.
select * from read_parquet('../../data/marts/fct_macro.parquet')
