# quant_dbt — 이식 가능한 dbt 변환 레이어

`data/` 의 원본 parquet(가격·유니버스·금리)을 **문서화·테스트된 마트**로 변환한다.
DuckDB(`dbt-duckdb`) 위에서 동작하며, **repo 의 Python 패키지와 완전히 분리**되어 있어
나중에 Airflow(또는 별도 repo)로 그대로 들어낼 수 있다.

## 이식성 설계
- **경로는 전부 환경변수** (기본값은 이 레포 기준):
  | env | 기본 | 의미 |
  |---|---|---|
  | `QUANT_DATA_DIR` | `../data` | 입력 원본 parquet 루트 |
  | `QUANT_MARTS_DIR` | `../data/marts` | 출력 external parquet 마트 |
  | `DBT_DUCKDB_PATH` | `target/quant.duckdb` | 개발용 DuckDB 파일 |
  | `DBT_PROFILES_DIR` | (—) | profiles.yml 위치(아래) |
- **profiles.yml 동봉** → `--profiles-dir .` 로 사용(홈 디렉터리 의존 X).
- **dbt 의존성 분리**: `requirements.txt`(dbt-core, dbt-duckdb). repo 의 `uv`/pyproject 와 무관.

## 로컬 실행
```bash
cd dbt
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
mkdir -p "${QUANT_MARTS_DIR:-../data/marts}"   # external 마트 출력 디렉터리(미리 존재해야 함)
dbt deps --profiles-dir .          # dbt_utils 설치
dbt build --profiles-dir .         # seed + run + test (입력=../data)
dbt docs generate --profiles-dir . && dbt docs serve   # 데이터 사전·리니지
```

## Airflow 이전 시
- 이 `dbt/` 디렉터리를 그대로 복사(또는 별도 repo) → 워커에 `requirements.txt` 설치.
- DAG 에서 env 만 주입: `QUANT_DATA_DIR`, `QUANT_MARTS_DIR`, `DBT_DUCKDB_PATH`, `DBT_PROFILES_DIR`.
- Cosmos / BashOperator(`dbt build`) 등 어느 방식이든 프로젝트 변경 불필요.

## 레이어
- `models/staging/` — 원본 1:1 정리(view). `_sources.yml` 에 원본 위치(env_var).
- `models/marts/` — `fct_prices` · `dim_universe` · `fct_rates` (external parquet 출력).
  `_marts.yml` = **데이터 사전 + 계약 테스트**(컬럼 의미, not_null, 조인키 relationships 등).
- `seeds/rate_series.csv` — 금리 시리즈 메타(국가·라벨·만기).

## 소비
- 백테스트/Python: `QUANT_MARTS_DIR` 의 parquet 을 그대로 읽음(polars).
- Evidence/DuckDB UI: 동일 마트 parquet 을 소스로.
