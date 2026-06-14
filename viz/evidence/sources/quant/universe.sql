-- dbt 마트 dim_universe_history (SCD2 소비 레이어).
select * from read_parquet('../../data/marts/dim_universe_history.parquet')
