select * from read_parquet('../../data/reference/rates/*.parquet', union_by_name=true, filename=true)
