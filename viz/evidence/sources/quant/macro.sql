-- dbt 마트 fct_macro (sk_id, sk_dim_macro_series, date, value). label 등 속성은 dim 조인으로 보강.
select * from read_parquet('../../data/marts/fct_macro.parquet')
