# 데이터 파이프라인 카탈로그

각 수집 파이프라인의 **목적 / 소스 / 주기 / 가용성**. 신호가치(★)는 국내 퀀트 기준.
수집 진입점: `scripts/ingest.py`. 무료 소스 = FDR(FinanceDataReader) · pykrx · FRED · (예정) ECOS·관세청.

> ⚠️ KRX STAT API 2026-05-21 인증 필수화 이후 **pykrx 통계 함수 전면 사용 금지** (내부 KrxWebIo → JSON 파싱 실패 → 빈 DataFrame).
> 투자자매매·VKOSPI·프로그램매매 등 KRX STAT 계열 수집 불가 → 대체 소스 필요. pykrx OHLCV(종목 일봉)는 정상.

---

## 1. 구현됨 (현재 동작)

| dataset | 목적 | 소스 | 주기 | CLI |
|---|---|---|---|---|
| **universe** | PIT 유니버스 멤버십(생존편향 방지) | FDR `StockListing` 스냅샷 누적 / CSV 수동주입 | 거래일(누적) / 수동 | `--dataset universe --source fdr\|csv` |
| **prices** | 종목 일별 OHLCV(수정주가) | FDR `DataReader` / pykrx OHLCV | 일 | `--dataset prices --source fdr\|pykrx` |
| **rates** | 무위험금리·국채(KR/US) | FRED via FDR | 일(US)/월(KR) | `--dataset rates --source fred --series ...` |
| **securities** | 종목 마스터(symbol→name·market) | FDR `StockListing` | 거래일(스냅샷) | `--dataset securities --source fdr --market ...` |
| **macro (FX·지수·원자재·크레딧·통화량·수출입 등)** | 매크로 시계열 29개 시리즈 | FDR / FRED / ECOS | 일·주·월 | `--dataset macro` |

**파생(별도 수집 불필요 — dbt 에서 계산)**:
- **ADR(등락비율)**: prices 에서 등락 종목 수 집계 → dbt 모델.
- **국내 신용스프레드(부분)**: 국고채(FRED/ECOS) − 회사채(ECOS) — 회사채는 ECOS 별도 시리즈 수집 필요.

---

## 3. 미수집 — 소스/키 필요

| 항목 | 신호가치 | 상태 |
|---|---|---|
| **투자자별 매매동향**(외인·기관·개인) | ★★★★★ | ❌ KRX STAT 차단 → KIS REST APP_KEY 발급 후 수집 |
| **프로그램 매매**(차익/비차익) | ★★★★★ | ❌ KRX STAT 차단 → KIS REST 시세분석 계열 |
| **VKOSPI**(변동성지수) | ★★★★☆ | ❌ KRX STAT 차단 → 네이버 보조 스크래핑(best-effort) |
| **선물 OI·외국인 선물포지션** | ★★★★☆ | ❌ KRX 파생 데이터 / 벤더 |
| **신용융자 잔고** | ★★★★☆ | ❌ 금융투자협회(KOFIA) |
| **고객예탁금·CMA 잔고** | ★★★★☆ | ❌ 금융투자협회(KOFIA) |
| **관세청 품목별 수출입** | ★★★★★ | ⚠️ 관세청 Open API — 키 미등록 |
| **국내 회사채 금리/신용스프레드** | ★★★★☆ | ⚠️ ECOS — 키 등록됨, 시리즈 미수집 |
| **DRAM 현물지수(DXI)** | ★★★☆☆ | ❌ 유료/스크래핑 |

---

## 4. 소스별 요약

| 소스 | 키 | 제공 | 주기 |
|---|---|---|---|
| **FDR** | 불필요 | 종목 OHLCV, FX, 지수, 상장목록 | 일 |
| **FRED**(FDR 경유) | 불필요 | 금리·국채, 달러인덱스, 원자재 | 일/월 |
| **한국은행 ECOS** | 등록됨 | 한국 M2 수집 중. 회사채·예탁금 미수집 | 일/월 |
| **pykrx** | 불필요 | 종목 OHLCV ✅ / KRX STAT 계열 ❌(차단) | 일 |
| **KRX MDC** | 스크래핑 | 투자자매매·프로그램·VKOSPI — KRX STAT 차단으로 불가 | — |
| **관세청 Open API** | 미등록 | 수출입 | 순/월 |
| **KOFIA** | 스크래핑 | 신용융자·예탁금 | 일 |

---

## 5. 권장 구현 순서

1. **KIS REST APP_KEY 발급** — 투자자매매·수급 수집 블로커 해제. KOSPI200 가격 이관도 가능.
2. **관세청 API 키 등록** — 수출입 수집. 신호가치 높음.
3. **ECOS 회사채 시리즈 추가** — `macro_series.csv` 에 시리즈 코드만 추가하면 수집 즉시 가능.
4. **KRX MDC / KOFIA** — 스크래핑 안정성 관리 필요. 우선순위 낮음.
