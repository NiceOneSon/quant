# quant_dbt — 이식 가능한 dbt 변환 레이어

`data/` 의 원본 parquet(가격·유니버스·금리·매크로)을 **문서화·테스트된 스타스키마 마트**로 변환한다.
DuckDB(`dbt-duckdb`) 위에서 동작하며, **repo 의 Python 패키지와 완전히 분리**되어 있어
나중에 Airflow(또는 별도 repo)로 그대로 들어낼 수 있다.

## 이식성 설계

경로는 전부 환경변수로 주입한다(기본값은 이 레포 기준):

| env | 기본 | 의미 |
|---|---|---|
| `QUANT_DATA_DIR` | `../data` | 입력 원본 parquet 루트 |
| `QUANT_MARTS_DIR` | `../data/marts` | 출력 external parquet 마트 |
| `DBT_DUCKDB_PATH` | `target/quant.duckdb` | 개발용 DuckDB 파일 |

- **profiles.yml 동봉** → `--profiles-dir .` 로 사용 (홈 디렉터리 의존 X).
- **dbt 의존성 분리**: `requirements.txt`(dbt-core, dbt-duckdb). repo 의 `uv`/pyproject 와 무관.

## 로컬 실행

```bash
# 방법 1: Makefile (프로젝트 루트) — 권장
make dbt-deps    # dbt_utils 설치
make dbt-build   # seed + run + test + Evidence 캐시 클리어

# 방법 2: 직접 (dbt/ 디렉터리 내)
cd dbt
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
mkdir -p "../data/marts"
dbt deps --profiles-dir .
dbt build --profiles-dir .        # PASS=92 목표
dbt docs generate --profiles-dir . && dbt docs serve  # 데이터 사전·리니지
```

> ⚠️ dbt 는 `dbt/` 디렉터리에서 실행해야 합니다. `../data` 기본 경로가 여기 기준이기 때문입니다.
> 프로젝트 루트에서 실행할 때는 `make dbt-build` 를 사용하거나 `QUANT_DATA_DIR` env 를 절대경로로 주입하세요.

## Airflow 이전 시

- 이 `dbt/` 디렉터리를 그대로 복사(또는 별도 repo) → 워커에 `requirements.txt` 설치.
- DAG 에서 env 만 주입: `QUANT_DATA_DIR`, `QUANT_MARTS_DIR`, `DBT_DUCKDB_PATH`.
- Cosmos / BashOperator(`dbt build`) 등 어느 방식이든 프로젝트 변경 불필요.

## 스키마 (raw → staging → intermediate → marts)

### 소스 (`source('raw')`)

| 소스 | 경로 | 컬럼 |
|---|---|---|
| `prices` | `data/processed/prices/*.parquet` | universe, symbol, date, OHLCV, close_raw |
| `universe` | `data/reference/universe/*.parquet` | universe, symbol, added, removed |
| `rates` | `data/reference/rates/*.parquet` | series, date, rate |
| `macro` | `data/reference/macro/*.parquet` | series, date, value |

### intermediate (ephemeral — 마트에 인라인)

| 모델 | 역할 |
|---|---|
| `int_universe_membership` | stg_universe + is_current 파생 |
| `int_universe_history` | SCD2 타임라인 구간 생성 (멤버십 + 갭) |
| `int_prices_pit` | stg_prices × int_universe_membership AS-OF 조인 |
| `int_rates_enriched` | stg_rates 통과 (label·tenor 는 dim 조인에서 파생) |

### 마트 (external parquet → `data/marts/`)

| 테이블 | sk_id | 컬럼 | FK |
|---|---|---|---|
| `dim_security` | `hash(symbol)` | symbol, name, market | — |
| `dim_universe_history` | `hash(universe, symbol, valid_from)` | universe, symbol, valid_from, valid_to, is_member, is_current | → dim_security |
| `dim_rate_series` | `hash(series)` | series, country, label, tenor | — |
| `dim_macro_series` | `hash(series)` | series, label, unit, country, category, source | — |
| `fct_prices` | `hash(date, universe, symbol)` | date, OHLCV, close_raw, is_halted, is_member_asof | → sk_dim_security, sk_dim_universe_history |
| `fct_rates` | `hash(series, date)` | date, rate | → sk_dim_rate_series |
| `fct_macro` | `hash(series, date)` | date, value | → sk_dim_macro_series |

**설계 원칙**:
- **정규화**: label/name/unit 등 속성은 dim 테이블에만. fct 는 측정값 + FK 만.
- **서로게이트 키**: dim → `sk_id`, fct FK → `sk_dim_<테이블명>`.
- **SCD2 (dim_universe_history)**: 멤버십 구간(`is_member=true`) + 갭 구간(`is_member=false`)으로 전체 타임라인 커버. `fct_prices.sk_dim_universe_history` 는 항상 non-null.
  - 갭 구간 valid_from sentinel: `1900-01-01` (편입 전 가격 행을 항상 포함).
- `is_halted = (volume = 0)` — staging 에서 파생 (Python raw 에는 없음).

### seeds

| 파일 | 역할 |
|---|---|
| `rate_series.csv` | FRED 금리 시리즈 메타 (series, country, label, tenor) |
| `macro_series.csv` | FX·지수·원자재·수출입 시리즈 메타 (29개 시리즈) |

`macro_series.csv` 카테고리: `fx` · `macro` · `commodity` · `index` · `credit` · `volatility` · `trade`

## 테스트 (`dbt build` = PASS 92)

- **not_null / unique**: 모든 dim.sk_id, fct.sk_id, fct.sk_dim_* (non-null 보장)
- **accepted_values**: market, country, category
- **relationships**: dim_universe_history.symbol → dim_security, fct_prices.sk_dim_universe_history → dim_universe_history 등
- **dbt_utils.expression_is_true**: OHLC 일관성(`high ≥ low`), 거래정지(`is_halted = (volume = 0)`), 금리 범위(-5~30%), close > 0
- **singular tests**: `assert_universe_intervals_valid`, `assert_universe_no_overlap`, `assert_ohlc_consistency`

## 소비

- **백테스트/Python**: `QUANT_MARTS_DIR` 의 parquet 을 polars 로 직접 읽음.
- **Evidence/DuckDB UI**: 동일 마트 parquet 을 소스로 조회 (`viz/evidence/sources/quant/`).
