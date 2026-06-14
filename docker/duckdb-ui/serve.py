"""DuckDB UI 서버를 컨테이너에서 띄우고 살려둔다. 등록할 뷰는 views.yaml 에서 읽는다.

뷰 매핑은 코드가 아니라 YAML(views.yaml)에 둔다: schema = dbt 레이어, table = dbt 모델명,
값 = DATA_DIR 기준 parquet 경로. db 는 기본(main) 유지.

UI 서버는 IPv6 루프백(::1:UI_PORT)에만 바인딩되므로 컨테이너에서는 socat 이 외부로 브리지한다
(entrypoint 참고). 이 스크립트는 뷰 생성 + UI 서버 시작 후 프로세스를 살려둔다.
"""

import glob
import os
import time

import duckdb
import yaml

DB = os.environ.get("DUCKDB_DB", "/work/quant.duckdb")
PORT = int(os.environ.get("UI_PORT", "4213"))
DATA = os.environ.get("DATA_DIR", "/data")
VIEWS_CONFIG = os.environ.get("VIEWS_CONFIG", "/app/views.yaml")

con = duckdb.connect(DB)
con.execute("INSTALL ui")
con.execute("LOAD ui")
con.execute(f"SET ui_local_port={PORT}")

with open(VIEWS_CONFIG, encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}

# schema = dbt 레이어, table = dbt 모델명. 파일이 없으면 건너뛴다(먼저 dbt build).
for schema, tables in (cfg.get("schemas") or {}).items():
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    for table, relpath in (tables or {}).items():
        pattern = f"{DATA}/{relpath}"
        if glob.glob(pattern):
            con.execute(
                f'CREATE OR REPLACE VIEW "{schema}"."{table}" AS '
                f"SELECT * FROM read_parquet('{pattern}')"
            )
            print(f"[view] {schema}.{table} <- {pattern}", flush=True)
        else:
            print(f"[skip] {schema}.{table}: no parquet at {pattern}", flush=True)

# 기본 스키마(search_path) 설정 → UI 에서 접두어 없이 마트 조회.
default_schema = cfg.get("default_schema")
if default_schema:
    con.execute(f"SET search_path = '{default_schema}'")
    current = con.execute("SELECT current_schema()").fetchone()
    print(f"[default] search_path={default_schema} (current_schema={current[0]})", flush=True)

msg = con.execute("CALL start_ui_server()").fetchone()
print(msg[0] if msg else "UI server started", flush=True)
print(f"[serve] bound 127.0.0.1:{PORT} (socat bridges to host). Keeping alive.", flush=True)

while True:
    time.sleep(3600)
