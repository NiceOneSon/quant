-- dbt 마트 dim_universe_history. 유니버스 멤버십 이력.
select * from read_parquet('../../data/marts/dim_universe_history.parquet')
