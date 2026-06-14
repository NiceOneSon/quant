# 데이터 파이프라인 카탈로그

각 수집 파이프라인의 **목적 / 소스 / 주기 / 가용성**. 신호가치(★)는 국내 퀀트 기준.
수집 진입점: `scripts/ingest.py`. 무료 소스 = FDR(FinanceDataReader) · pykrx · FRED · (예정) ECOS·관세청.

> ⚠️ pykrx 의 **지수·상장목록·수급 endpoint 는 현재 KRX 회귀로 깨져 있음**(실측: 빈 결과 / `KeyError '지수명'`).
> 따라서 지수·투자자매매·VKOSPI 등은 pykrx 로 수집 불가 → 대체 소스 필요. pykrx OHLCV(종목 일봉)는 정상.

---

## 1. 구현됨 (현재 동작)

| dataset | 목적 | 소스 | 주기 | CLI |
|---|---|---|---|---|
| **universe** | PIT 유니버스 멤버십(생존편향 방지) | FDR `StockListing` 스냅샷 누적 / CSV 수동주입 | 거래일(누적) / 수동 | `--dataset universe --source fdr\|csv` |
| **prices** | 종목 일별 OHLCV(수정주가) | FDR `DataReader` / pykrx OHLCV | 일 | `--dataset prices --source fdr\|pykrx` |
| **rates** | 무위험금리·국채(KR/US) | FRED via FDR | 일(US)/월(KR) | `--dataset rates --source fred --series ...` |
| **securities** | 종목 마스터(symbol→name·market) | FDR `StockListing` | 거래일(스냅샷) | `--dataset securities --source fdr --market ...` |

---

## 2. 요청 — 무료로 수집 가능 (구현 예정, 기존 FDR/FRED 패턴에 적합)

전부 시계열이라 기존 rates 패턴(시리즈별 parquet → dbt 마트)으로 흡수 가능.

| dataset | 항목 | 소스(코드) | 주기 | 신호가치 |
|---|---|---|---|---|
| **fx** | USD/KRW, USD/JPY | FDR `DataReader('USD/KRW')` 등 | 일 | ★★★★★ |
| **macro** | 달러인덱스 DXY | FRED `DTWEXBGS` | 일 | ★★★★★ |
| **commodity** | WTI 유가, 구리 | FRED `DCOILWTICO`, `PCOPPUSDM` | 일/월 | ★★★☆ |
| **index** | KOSPI, KOSPI200, KOSDAQ | FDR `KS11`/`KS200`/`KQ11` | 일 | 벤치마크·베타 |

**파생(별도 수집 불필요 — dbt 에서 계산)**:
- **ADR(등락비율)**: prices 에서 등락 종목 수 집계 → dbt 모델.
- **국내 신용스프레드(부분)**: 국고채(FRED/ECOS) − 회사채(ECOS) — 회사채는 ECOS 필요(아래).

---

## 3. 요청 — 무료 즉시 불가 (별도 소스/키 필요 또는 pykrx 깨짐)

| 항목 | 신호가치 | 상태 / 필요한 소스 |
|---|---|---|
| **투자자별 매매동향**(외인·기관·개인) | ★★★★★ | ❌ pykrx `get_market_trading_value_by_date` 빈 결과(깨짐) → **KRX 정보데이터시스템(MDC) API** 또는 데이터 벤더 |
| **프로그램 매매**(차익/비차익) | ★★★★★ | ❌ KRX MDC / 벤더 |
| **VKOSPI**(변동성지수) | ★★★★☆ | ❌ pykrx 지수 endpoint 깨짐 → KRX MDC / 별도 |
| **선물 OI·외국인 선물포지션** | ★★★★☆ | ❌ KRX 파생 데이터 / 벤더 |
| **신용융자 잔고** | ★★★★☆ | ❌ 금융투자협회(KOFIA) / KRX |
| **고객예탁금·CMA 잔고** | ★★★★☆ | ❌ 금융투자협회(KOFIA) |
| **수출입 데이터**(관세청) | ★★★★★ | ⚠️ **관세청 Open API**(무료, 별도 키) → 신규 소스 어댑터 필요 |
| **국내 회사채 금리/신용스프레드** | ★★★★☆ | ⚠️ **한국은행 ECOS API**(무료, 별도 키) → 신규 어댑터 |
| **엔 캐리(USD/JPY)** | ★★★★★ | ✅ FDR(2절 fx 에 포함) |
| **DRAM 현물지수(DXI)** | ★★★☆☆ | ❌ 유료/스크래핑 |

---

## 4. 소스별 요약

| 소스 | 키 | 제공 | 주기 |
|---|---|---|---|
| **FDR** | 불필요 | 종목 OHLCV, FX, 지수, 상장목록 | 일 |
| **FRED**(FDR 경유) | 불필요 | 금리·국채, 달러인덱스, 원자재 | 일/월 |
| **pykrx** | 불필요 | 종목 OHLCV ✅ / 지수·수급·상장목록 ❌(깨짐) | 일 |
| **KRX MDC** | (스크래핑) | 투자자매매·프로그램·VKOSPI·선물 | 일/실시간 |
| **한국은행 ECOS** | 무료 키 | 회사채·예탁금·매크로 | 일/월 |
| **관세청 Open API** | 무료 키 | 수출입 | 순/월 |
| **KOFIA** | (스크래핑) | 신용융자·예탁금 | 일 |

---

## 5. 권장 구현 순서

1. **(2절) FDR/FRED 시계열 일괄 수집** — fx·macro·commodity·index. 기존 패턴에 바로 흡수, 가성비 최고. *(단, ETL→ELT 리팩터링과 함께 진행 권장 — 신규 수집기를 ELT 스타일로)*
2. **관세청·ECOS 어댑터**(무료 키) — 수출입·회사채. 신호가치 높음.
3. **KRX MDC 어댑터** — 투자자매매·프로그램·VKOSPI·선물. 가장 가치 높으나 스크래핑 안정성 관리 필요.
