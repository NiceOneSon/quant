"""DuckDB UI 서버를 컨테이너에서 띄우고 살려둔다. data/ 의 parquet 을 뷰로 노출한다.

UI 서버는 127.0.0.1:UI_PORT 에만 바인딩되므로(외부 바인드 옵션 없음), 컨테이너에서는
socat 이 0.0.0.0 → 127.0.0.1 로 브리지한다(entrypoint 참고). 이 스크립트는 뷰 생성 + UI
서버 시작 후 프로세스를 살려둔다(서버는 백그라운드 스레드라 메인이 죽으면 같이 죽음).
"""

import glob
import os
import time

import duckdb

DB = os.environ.get("DUCKDB_DB", "/work/quant.duckdb")
PORT = int(os.environ.get("UI_PORT", "4213"))
DATA = os.environ.get("DATA_DIR", "/data")

con = duckdb.connect(DB)
con.execute("INSTALL ui")
con.execute("LOAD ui")
con.execute(f"SET ui_local_port={PORT}")

# data/ 의 parquet 을 바로 쿼리 가능한 뷰로 등록. 파일이 없으면 건너뛴다.
VIEWS = {
    "prices": f"{DATA}/processed/prices/*.parquet",
    "universe": f"{DATA}/reference/universe/*.parquet",
    "universe_snapshots": f"{DATA}/reference/universe_snapshots/*.parquet",
    "rates": f"{DATA}/reference/rates/*.parquet",
}
for name, pattern in VIEWS.items():
    if glob.glob(pattern):
        con.execute(
            f"CREATE OR REPLACE VIEW {name} AS "
            f"SELECT * FROM read_parquet('{pattern}', union_by_name=true, filename=true)"
        )
        print(f"[view] {name} <- {pattern}", flush=True)
    else:
        print(f"[skip] {name}: no parquet at {pattern}", flush=True)

msg = con.execute("CALL start_ui_server()").fetchone()
print(msg[0] if msg else "UI server started", flush=True)
print(f"[serve] bound 127.0.0.1:{PORT} (socat bridges to host). Keeping alive.", flush=True)

while True:
    time.sleep(3600)
