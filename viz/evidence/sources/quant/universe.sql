-- dbt 마트 dim_universe (소비 레이어).
select * from read_parquet('../../data/marts/dim_universe.parquet')
