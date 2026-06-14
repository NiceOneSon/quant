-- dim_security: 종목 마스터 (sk_id, symbol, name, market)
select * from read_parquet('../../data/marts/dim_security.parquet')
