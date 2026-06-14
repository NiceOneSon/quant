-- dim_rate_series: 금리 시리즈 마스터. series 코드 제외, label 기준으로만 조회.
select sk_id, label, country, tenor from read_parquet('../../data/marts/dim_rate_series.parquet')
