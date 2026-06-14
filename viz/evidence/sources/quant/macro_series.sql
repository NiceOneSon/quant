-- dim_macro_series: 매크로 시리즈 마스터. series 코드 제외, label 기준으로만 조회.
select sk_id, label, unit, country, category, source, frequency from read_parquet('../../data/marts/dim_macro_series.parquet')
