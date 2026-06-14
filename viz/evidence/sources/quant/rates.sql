-- dbt 마트 fct_rates (sk_id, sk_dim_rate_series, date, rate). label 등 속성은 dim 조인으로 보강.
select * from read_parquet('../../data/marts/fct_rates.parquet')
