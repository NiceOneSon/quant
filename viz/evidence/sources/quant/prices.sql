-- dbt 마트 fct_prices (소비 레이어). 경로는 프로젝트 루트 기준 상대(Docker 동일 레이아웃).
select * from read_parquet('../../data/marts/fct_prices.parquet')
