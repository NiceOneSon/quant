-- dbt 마트 dim_universe_history (SCD2 소비 레이어).
-- is_member=false 갭 구간은 fct_prices range join 전용 내부 구현 — Evidence에서 제외.
select * from read_parquet('../../data/marts/dim_universe_history.parquet')
where is_member = true
