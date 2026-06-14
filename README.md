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
```

### 저장 레이아웃 & 식별 키
| 경로 | 키 컬럼 | 비고 |
|---|---|---|
| `data/reference/universe/<name>.parquet` | `universe, symbol, added, removed` | PIT 멤버십 구간 |
| `data/reference/universe_snapshots/<name>.parquet` | `asof, symbol` | 스냅샷 누적 로그 |
| `data/processed/prices/<name>.parquet` | `universe, symbol, date` | 수정주가 OHLCV + `is_halted` |
| `data/reference/rates/<series>.parquet` | `series, country, date` | 연율 %, `country`=KR/US |
| `data/marts/*.parquet` | — | dbt 출력 (아래) |

- **`symbol`** = KRX 6자리 상장코드(0패딩 문자열, 예 `005930`). 가격·유니버스 공통 조인 키.
- 데이터셋은 `filename` 이 아니라 **명시적 키 컬럼**(`universe`/`series`/`country`)으로 구분.

---

## 3. 백테스트 (`scripts/backtest.py`)

PIT-안전 수직 슬라이스: 모멘텀 → 상위 N 동일가중 롱온리 → **t+1 시가 체결(거래비용·슬리피지
반영, 거래정지 제외)** → 지표(CAGR/Sharpe/MDD).

**소비자(백테스트·대시보드)는 raw 가 아니라 dbt 마트를 읽는다** → 수집 후 `dbt build` 필요:

```bash
# 1) 수집(raw)         2) dbt 변환(마트)        3) 백테스트(마트 소비)
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source fdr
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset prices   --source fdr
( cd dbt && . .venv/bin/activate && dbt build --profiles-dir . )
uv run python scripts/backtest.py --config configs/backtest.yaml
```

> ⚠️ 유니버스가 생존편향 없이 구성돼야 성과가 신뢰됨. "현재 시총 상위" 같은 유니버스로 과거를
> 돌리면 가짜 알파가 나온다. 자세한 안전장치는 `CLAUDE.md`.

---

## 4. dbt 변환 레이어 (`dbt/`)

원본 parquet → **문서화·테스트된 마트**(`fct_prices`·`dim_universe`·`fct_rates`). DuckDB 기반,
**repo 의 Python 과 분리**되어 Airflow 로 그대로 이식 가능(경로는 env_var 주입). 상세는 `dbt/README.md`.

```bash
cd dbt
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
mkdir -p ../data/marts
dbt deps --profiles-dir . && dbt build --profiles-dir .   # seed + run + test
dbt docs generate --profiles-dir . && dbt docs serve      # 데이터 사전 + 리니지
```

`_marts.yml` 이 **데이터 사전(컬럼 의미) + 계약 테스트**(예: `fct_prices.symbol` ⊂
`dim_universe.symbol` relationships, 그레인 유일성, `country` accepted_values)를 강제한다.

---

## 5. 시각화 (Docker)

```bash
docker compose up -d --build            # DuckDB UI(4213) + Evidence(3000)
docker compose down
```

| UI | URL | 성격 |
|---|---|---|
| **DuckDB UI** | http://localhost:4213 | SQL 노트북 + 즉석 차트(탐색). `fct_prices`·`dim_universe`·`fct_rates` 뷰(main 스키마) 자동 등록 |
| **Evidence** | http://localhost:3000 | 코드형 BI 대시보드(`viz/evidence/pages/*.md`). 가격·유니버스·금리 페이지 |

- `data/` 는 **읽기전용** 마운트(시각화 전용).
- DuckDB UI 프런트엔드는 `ui.duckdb.org` 에서 로드(데이터는 로컬, 인터넷 필요).
- Evidence 대시보드 저작은 핫리로드로: `cd viz/evidence && npm install && npm run dev`.
- DuckDB UI 뷰 매핑은 `docker/duckdb-ui/views.yaml`(main 스키마, table=dbt 모델명).
- 예) `select date, close from fct_prices where universe = 'kospi40' and symbol = '005930'`

---

## 6. 디렉터리

```
.
├── CLAUDE.md              # 아키텍처·규칙·도메인 안전장치 (필독)
├── configs/               # 환경별 YAML (dev/backtest)
├── scripts/               # CLI 진입점: ingest.py, backtest.py
├── src/
│   ├── data_layer/        # 수집·저장·조회(PIT) + 소스 어댑터(pykrx/fdr/fred)
│   ├── research/          # signals/ · combine · validation · backtest
│   ├── portfolio/         # optimizer(제약)
│   ├── execution/         # 집행 (기본 dry-run)
│   ├── risk/              # 사전 체크
│   └── common/            # config · logging
├── dbt/                   # 이식형 dbt 변환 레이어 (DuckDB)
├── viz/evidence/          # Evidence.dev 대시보드
├── docker/duckdb-ui/      # DuckDB UI 컨테이너
├── docker-compose.yml     # duckdb-ui + evidence
├── data/                  # ⚠️ gitignored. raw/processed/reference/marts parquet
└── tests/                 # src 구조 미러
```

`.env.example` 을 `.env` 로 복사해 시크릿을 채우세요 (`.env`·`data/` 는 커밋 금지).

---

## 7. 알려진 제약 (무료 데이터 소스)

- **pykrx 지수/상장목록 endpoint 깨짐** (pandas 2/3 무관, KRX 회귀) → 유니버스는 **FDR** 사용. pykrx OHLCV 는 정상.
- **원본가(close_raw) 미제공** — pykrx `adjusted=False`·FDR 모두 수정주가만 → `close_raw` 는 null(수정계수 복원 불가).
- **FDR 유니버스 스냅샷은 현재 상장목록만** → 단일 스냅샷은 생존편향. 누적(`universe_snapshots`) 또는 과거 멤버십 CSV 주입으로 PIT 확보.
- **한국 무위험금리(FRED)는 월별**. 미국채/Fed funds 는 일별.
- 정확한 KOSPI200 편입/퇴출 이력은 무료로는 부재 — 스냅샷 누적 또는 별도 소스 필요.
