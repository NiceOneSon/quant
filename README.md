# quant

모듈형 퀀트 투자 시스템 (데이터 수집 → 시그널 → 포트폴리오 → 집행 + 리스크).
아키텍처·코딩 규칙·도메인 안전장치는 **`CLAUDE.md`** 참고.

```
수집(Python) → 원본 parquet(data/) → dbt 변환·검증(DuckDB) → 마트
                     │                                          │
                     └── 백테스트 엔진 ──── 성과지표             └── 시각화(DuckDB UI / Evidence)
```

---

## 1. 빠른 시작

```bash
uv sync --extra dev                      # 코어 + 테스트/린트
uv sync --extra dev --extra data --extra viz   # + 데이터 수집·시각화까지

uv run pytest                            # 테스트
uv run ruff check . && uv run mypy src   # 린트·타입 (커밋 전 필수)
```

uv extras: **`dev`**(pytest/ruff/mypy) · **`data`**(pykrx·FinanceDataReader·FRED) · **`viz`**(duckdb).

---

## 2. 데이터 수집 (`scripts/ingest.py`)

모든 데이터는 `data/` 에 parquet 으로 적재된다(gitignored). 소스 어댑터는 같은 Protocol 을
구현하며 네트워크 호출은 어댑터에만 격리(테스트는 모킹).

```bash
# 유니버스 — FDR 현재 상장목록 스냅샷을 누적(앞으로 PIT 축적). 시장 단위(kospi/kosdaq/krx).
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source fdr
#   또는 과거 멤버십 직접 주입: --source csv  (data/raw/universe/<name>.csv: symbol,added,removed)

# 가격 — 유니버스 종목의 수정주가 OHLCV (FDR 또는 pykrx)
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset prices --source fdr

# 금리 — FRED(키 불필요). 기본 한국 3M, --series 로 미국채(DGS10 등) 지정
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset rates --source fred --series DGS10

# 매크로 — FX(USD/KRW·USD/JPY), 달러인덱스(DXY), WTI·구리, KOSPI/KOSPI200/KOSDAQ
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset macro
```

### 저장 레이아웃 & 식별 키
| 경로 | 키 컬럼 | 비고 |
|---|---|---|
| `data/reference/universe/<name>.parquet` | `universe, symbol, added, removed` | PIT 멤버십 구간 |
| `data/reference/universe_snapshots/<name>.parquet` | `asof, symbol` | 스냅샷 누적 로그 |
| `data/processed/prices/<name>.parquet` | `universe, symbol, date` | 수정주가 OHLCV |
| `data/reference/rates/<series>.parquet` | `series, date, rate` | 연율 % |
| `data/reference/macro/<series>.parquet` | `series, date, value` | FX·지수·원자재 |
| `data/marts/*.parquet` | — | dbt 출력 (아래) |

- **`symbol`** = KRX 6자리 상장코드(0패딩 문자열, 예 `005930`). 가격·유니버스 공통 조인 키.

---

## 3. 백테스트 (`scripts/backtest.py`)

PIT-안전 수직 슬라이스: 모멘텀 → 상위 N 동일가중 롱온리 → **t+1 시가 체결(거래비용·슬리피지
반영, 거래정지 제외)** → 지표(CAGR/Sharpe/MDD).

**소비자(백테스트·대시보드)는 raw 가 아니라 dbt 마트를 읽는다** → 수집 후 `dbt build` 필요:

```bash
# 1) 수집(raw)         2) dbt 변환(마트)        3) 백테스트(마트 소비)
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source fdr
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset prices   --source fdr
make dbt-build
uv run python scripts/backtest.py --config configs/backtest.yaml
```

> ⚠️ 유니버스가 생존편향 없이 구성돼야 성과가 신뢰됨. "현재 시총 상위" 같은 유니버스로 과거를
> 돌리면 가짜 알파가 나온다. 자세한 안전장치는 `CLAUDE.md`.

---

## 4. dbt 변환 레이어 (`dbt/`)

원본 parquet → **문서화·테스트된 스타스키마 마트**. DuckDB 기반, repo 의 Python 과 분리되어
Airflow 로 그대로 이식 가능(경로는 env_var 주입). 상세는 `dbt/README.md`.

### 마트 스키마 (서로게이트 키 포함)

| 테이블 | sk | 비고 |
|---|---|---|
| `dim_security` | `sk_id = hash(symbol)` | 종목 마스터(이름·시장) |
| `dim_universe` | `sk_id = hash(universe,symbol,added)` | PIT 멤버십 구간 |
| `dim_rate_series` | `sk_id = hash(series)` | 금리 시리즈 메타(FRED) |
| `dim_macro_series` | `sk_id = hash(series)` | 매크로 시리즈 메타(FX·지수·원자재) |
| `fct_prices` | → `sk_dim_security`, `sk_dim_universe` | 일별 수정주가 OHLCV |
| `fct_rates` | → `sk_dim_rate_series` | 금리 관측값 |
| `fct_macro` | → `sk_dim_macro_series` | FX·지수·원자재 관측값 |

### dbt 명령어 (프로젝트 루트)
```bash
# Makefile 경유 — CWD·프로파일 자동 설정
make dbt-deps    # dbt_utils 패키지 설치
make dbt-build   # seed + run + test (PASS=78 목표)
make dbt-docs    # 데이터 사전 + 리니지 브라우저

# 또는 직접 실행 (dbt/ 디렉터리에서)
cd dbt && . .venv/bin/activate
dbt build --profiles-dir .
```

---

## 5. 시각화 (Docker)

```bash
docker compose up -d --build            # DuckDB UI(4213) + Evidence(3000)
docker compose down
```

| UI | URL | 성격 |
|---|---|---|
| **DuckDB UI** | http://localhost:4213 | SQL 노트북 + 즉석 차트(탐색) |
| **Evidence** | http://localhost:3000 | 코드형 BI 대시보드 |

Evidence 페이지:
- **가격** `/prices` — 종목별 OHLCV·거래량·거래정지(종목명 JOIN 포함)
- **유니버스** `/universe` — 구성 종목·소스별 규모
- **금리** `/rates` — 무위험금리·국채 수익률 곡선·장단기 스프레드
- **매크로** `/macro` — FX(달러-원/엔)·달러인덱스·WTI·구리·KOSPI/KOSDAQ

Evidence 저작(핫리로드):
```bash
cd viz/evidence && npm install && npm run dev
```

---

## 6. 디렉터리

```
.
├── CLAUDE.md              # 아키텍처·규칙·도메인 안전장치 (필독)
├── Makefile               # dbt 편의 명령어 (make dbt-build 등)
├── configs/               # 환경별 YAML (dev/backtest)
├── scripts/               # CLI 진입점: ingest.py, backtest.py
├── src/
│   ├── data_layer/        # 수집·저장·조회(PIT) + 소스 어댑터(pykrx/fdr/fred)
│   ├── research/          # signals/ · combine · validation · backtest
│   ├── portfolio/         # optimizer(제약)
│   ├── execution/         # 집행 (기본 dry-run)
│   ├── risk/              # 사전 체크
│   └── common/            # config · logging
├── dbt/                   # 이식형 dbt 변환 레이어 (DuckDB, PASS=78)
├── viz/evidence/          # Evidence.dev 대시보드 (4개 페이지)
├── docker/duckdb-ui/      # DuckDB UI 컨테이너
├── docker-compose.yml     # duckdb-ui + evidence
├── data/                  # ⚠️ gitignored. raw/processed/reference/marts parquet
└── tests/                 # src 구조 미러
```

`.env.example` 을 `.env` 로 복사해 시크릿을 채우세요 (`.env`·`data/` 는 커밋 금지).

---

## 7. 알려진 제약 (무료 데이터 소스)

- **pykrx 지수/상장목록 endpoint 깨짐** (pandas 2/3 무관, KRX 회귀) → 유니버스는 **FDR** 사용. pykrx OHLCV 는 정상.
- **원본가(close_raw) 미제공** — pykrx `adjusted=False`·FDR 모두 수정주가만 → `close_raw` 는 null.
- **FDR 수정주가 반올림** — `high` vs `close` 가 1원 범위에서 역전 가능(거래비용 외 영향 없음).
- **거래정지일 OHLV=0** — FDR: 거래정지 시 `open/high/low=0`, `close`=기준가 이월. `is_halted=true` 로 식별.
- **FDR 유니버스 스냅샷은 현재 상장목록만** → 단일 스냅샷은 생존편향. 누적(`universe_snapshots`) 또는 과거 멤버십 CSV 주입으로 PIT 확보.
- **한국 무위험금리(FRED)는 월별**. 미국채/Fed funds 는 일별.
- 정확한 KOSPI200 편입/퇴출 이력은 무료로는 부재 — 스냅샷 누적 또는 별도 소스 필요.
