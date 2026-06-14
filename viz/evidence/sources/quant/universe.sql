select * from read_parquet('../../data/reference/universe/*.parquet', union_by_name=true, filename=true)
