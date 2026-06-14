-- data/processed/prices/*.parquet (경로는 프로젝트 루트 기준 상대; Docker 도 동일 레이아웃)
select * from read_parquet('../../data/processed/prices/*.parquet', union_by_name=true, filename=true)
