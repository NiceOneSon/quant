# 데이터 소스 참조

수집 소스·주기·경로·freshness 임계값 일람. `macro_series.csv` / `rate_series.csv` seed가 소스 오브 트루스.

---

## 수집 명령어

```bash
# 가격 (수정주가 OHLCV)
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset prices --source fdr

# 유니버스 멤버십 스냅샷
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset universe --source fdr

# 금리 (FRED)
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset rates

# 매크로 전체 (macro_series.csv 기준)
uv run python scripts/ingest.py --config configs/backtest.yaml --dataset macro
```

---

## 가격 (`data/processed/prices/`)

| 항목 | 내용 |
|---|---|
| 소스 | FDR (FinanceDataReader) |
| 주기 | 일별 (장마감 후) |
| 키 | `universe, symbol, date` |
| freshness | warn 3일 / error 7일 |
| 비고 | 수정주가 OHLCV. `close_raw` 미제공(null). KIS APP_KEY 발급 후 대체 예정 |

---

## 유니버스 (`data/reference/universe/`)

| 항목 | 내용 |
|---|---|
| 소스 | FDR (현재 상장목록 스냅샷) / CSV 직접 주입 |
| 주기 | KOSPI200 정기 리밸런싱 연 2회 (6월·12월) + 수시 |
| 키 | `universe, symbol, added, removed` |
| freshness | warn 45일 / error 180일 |
| 비고 | 단일 스냅샷은 생존편향 유발. 정확한 PIT 이력은 과거 멤버십 CSV 주입 필요 |

---

## 금리 (`data/reference/rates/`)

| series | label | 주기 | 소스 |
|---|---|---|---|
| IR3TIB01KRM156N | 한국 3M 은행간금리 (CD91일) | 월별 | FRED |
| DGS3MO | 미국 3M 국채 | 일별 | FRED |
| DGS2 | 미국 2Y 국채 | 일별 | FRED |
| DGS10 | 미국 10Y 국채 | 일별 | FRED |
| DFF | 미국 연방기금금리 | 일별 | FRED |
| SOFR | SOFR | 일별 | FRED |

**freshness**: warn 10일 / error 21일 (일별~월별 혼재, 공휴일 버퍼 포함)

---

## 매크로 (`data/reference/macro/`)

**freshness 임계값**: daily → error 7일 / weekly → error 14일 / monthly → error 120일
(`assert_macro_series_freshness` dbt 테스트로 자동 검증)

### FX

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| USD/KRW | 달러-원 환율 | KRW | daily | FDR |
| USD/JPY | 달러-엔 환율 | JPY | daily | FDR |
| EUR/USD | 유로-달러 환율 | USD | daily | FDR |
| USD/CNY | 달러-위안 환율 | CNY | daily | FDR |

### 달러인덱스 / 변동성

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| DTWEXBGS | 달러인덱스 DXY | index | weekly | FRED |
| VIX | VIX 변동성 지수 | index | daily | FDR |

### 크레딧 스프레드

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| BAMLH0A0HYM2EY | 미국 HY OAS | % | daily | FRED |
| BAMLC0A0CM | 미국 IG OAS | % | daily | FRED |

### 인플레이션 / 매크로

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| CPIAUCSL | 미국 CPI | index | monthly | FRED |
| PCEPI | 미국 PCE | index | monthly | FRED |
| T10YIE | 미국 10Y 기대인플레이션 | % | daily | FRED |
| T5YIFR | 미국 5y5y 기대인플레이션 | % | daily | FRED |
| PAYEMS | 미국 비농업 고용(NFP) | thousands | monthly | FRED |
| ICSA | 미국 실업수당청구 | thousands | weekly | FRED |
| M2SL | 미국 M2 | billion USD | monthly | FRED |
| WALCL | 연준 대차대조표 | million USD | weekly | FRED |

### 원자재

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| DCOILWTICO | WTI 원유가 | USD/bbl | daily | FRED |
| DHHNGSP | 천연가스 | USD/MMBtu | daily | FRED |
| PCOPPUSDM | 구리 현물가 (LME) | USD/MT | monthly | FRED |
| HG=F | 구리 선물 (COMEX) | USD/lb | daily | FDR |
| Gold | 금 (LBMA 오후가) | USD/troy oz | daily | FDR |
| SLV | 은 ETF (iShares SLV) | USD | daily | FDR |

### 국내 지수

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| KS11 | KOSPI 지수 | point | daily | FDR |
| KS200 | KOSPI200 지수 | point | daily | FDR |
| KQ11 | KOSDAQ 지수 | point | daily | FDR |

### 한국 수출입

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| XTEXVA01KRM659S | 한국 수출 증감률 YoY | % | monthly | FRED |
| XTIMVA01KRM659S | 한국 수입 증감률 YoY | % | monthly | FRED |

> FRED 발표 lag 최대 3개월 이상 — freshness error 임계값 120일 적용

### 한국 통화량

| series | label | 단위 | 주기 | 소스 |
|---|---|---|---|---|
| 161Y006:BBHA00:M | 한국 M2 (광의통화 평잔) | 십억원 | monthly | ECOS |

> ECOS API KEY 등록됨 (`ECOS_KEY` env). Rate limit 300req/3min → throttle 1.1s 적용.

---

## 미수집 지표 (우선순위 순)

| 지표 | 이유 | 대체 방안 |
|---|---|---|
| 투자자별 매매동향 (기관·외국인) | KRX 차단, KIS 미발급 | KIS REST APP_KEY 발급 후 수집 |
| 프로그램매매 (차익/비차익) | KRX 차단 | KIS REST 시세분석 계열 |
| VKOSPI | KRX 차단 | 네이버 보조 스크래핑 (best-effort) |
| ADR (등락비율) | KRX 차단 | fct_prices 기반 자체 계산 |
| 국내 크레딧 스프레드 | ECOS 시리즈 미수집 | `macro_series.csv`에 ECOS 시리즈 코드 추가 |
| 관세청 품목별 수출입 | API 키 미등록 | 관세청 Open API 무료 발급 |

---

## KRX 접근 제한 (2026-05-21~)

`dbms/MDC/STAT/standard/*` 전체 로그인 인증 필수. 무인증 호출 시 HTTP 400 + `LOGOUT` 응답.
과도 접속 시 **IP 영구 차단**. **pykrx 통계 함수 및 KRX STAT 직접 호출 금지.**

`dbms/comm/finder/*` (단순 종목 검색) 만 무인증 가능.
