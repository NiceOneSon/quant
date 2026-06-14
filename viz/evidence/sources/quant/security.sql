-- dim_security: 종목 마스터. symbol 코드 제외, name 기준으로만 조회.
select sk_id, name, market from read_parquet('../../data/marts/dim_security.parquet')
