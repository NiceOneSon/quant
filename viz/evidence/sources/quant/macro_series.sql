-- dim_macro_series: 매크로 시리즈 마스터 (sk_id, series, label, unit, country, category)
select * from read_parquet('../../data/marts/dim_macro_series.parquet')
