-- dim_rate_series: 금리 시리즈 마스터 (sk_id, series, country, label, tenor)
select * from read_parquet('../../data/marts/dim_rate_series.parquet')
