# CLAUDE.md

이 파일은 Claude Code가 매 세션 자동으로 읽는 프로젝트 가이드입니다.
간결함이 곧 성능입니다 — 불필요한 설명은 넣지 말고, 실제 규칙·명령어·제약만 유지하세요.

> 채워 넣을 곳: `<...>` 로 표시된 항목은 실제 값으로 교체하세요.

---

## 1. 프로젝트 개요

`<프로젝트명>` 은 퀀트 투자 시스템입니다. 데이터 수집부터 신호 생성, 포트폴리오 구성,
주문 집행까지를 **느슨하게 결합된 모듈형 파이프라인**으로 구현합니다.

핵심 원칙:
- **재현성(reproducibility)**: 같은 입력 → 같은 결과. 시드 고정, 데이터 버전 고정.
- **연구-운영 일치(research-production parity)**: 백테스트와 라이브가 동일 코드 경로를 쓴다.
- **시점 정확성(point-in-time)**: 과거 특정 시점에 실제로 알 수 있었던 데이터만 사용한다.

---

## 2. 아키텍처 / 디렉터리 구조

```
.
├── CLAUDE.md
├── pyproject.toml
├── configs/            # 환경별 YAML 설정 (dev / backtest / live)
├── data/               # ⚠️ gitignored. raw/processed 데이터. 절대 커밋 금지
├── notebooks/          # 탐색용 노트북. 운영 로직을 여기 두지 말 것
├── scripts/            # CLI 진입점 (backtest, live, ingest 등)
├── src/
│   ├── data_layer/     # 수집·저장·정제, point-in-time 보장
│   ├── research/       # 피처/시그널, 팩터 모델, 백테스트 엔진
│   ├── portfolio/      # 최적화, 리스크 모델, 포지션 산출
│   ├── execution/      # OMS/EMS 어댑터, 스마트 라우팅, TCA
│   ├── risk/           # 사전 한도 체크, 실시간 모니터링, VaR/스트레스
│   └── common/         # config, logging, 공통 타입, 유틸
└── tests/              # src 구조를 미러링
```

레이어 간 의존 방향은 단방향입니다: `data_layer → research → portfolio → execution`.
`risk` 와 `common` 은 모든 레이어가 의존할 수 있습니다. **역방향 import 금지.**

---

## 3. 기술 스택

- 언어: Python 3.11+
- 패키지/가상환경: `uv`
- 데이터: `polars` 우선, 호환 필요 시 `pandas`. 수치 연산 `numpy`
- 백테스트: `<vectorbt / 자체 엔진 등>`
- 설정: `pydantic` + YAML (`configs/`)
- 테스트: `pytest`, 린트 `ruff`, 타입 `mypy`

---

## 4. 자주 쓰는 명령어

```bash
# 환경 설정
uv sync

# 테스트 (커밋 전 필수)
uv run pytest
uv run pytest tests/research/         # 특정 레이어만

# 린트 + 포맷 + 타입 (커밋 전 필수)
uv run ruff check . && uv run ruff format . && uv run mypy src

# 백테스트 실행
uv run python scripts/backtest.py --config configs/backtest.yaml

# 데이터 수집
uv run python scripts/ingest.py --config configs/dev.yaml
```

작업 완료 시 위 테스트/린트/타입 체크를 **모두 통과**시킨 뒤 마무리하세요.

### dbt 변경 후 필수 후속 작업

dbt 모델·시드·소스를 변경한 뒤에는 **반드시 아래 순서로 실행**한다.

```bash
# 1) dbt 빌드 (마트 parquet 재생성 + Evidence 캐시 클리어 포함)
make dbt-build

# 2) DuckDB UI 뷰 갱신 — 테이블 추가·삭제 시에만 (컨테이너 재시작 필요)
docker compose restart duckdb-ui

# 3) Evidence 소스 재빌드 — 소스 SQL·pages 변경 후 항상 수행
cd viz/evidence && npm run sources
```

- `make dbt-build` 는 dbt build + `gen_duckdb_views.py` + Evidence 3개 캐시 클리어를 한 번에 수행한다.
- Evidence 소스(`npm run sources`)는 캐시 클리어 후 반드시 재실행해야 한다. 누락 시 페이지가 오래된 parquet을 참조하거나 ENOENT 오류가 발생한다.
- DuckDB UI는 컨테이너 기동 시 `views.yaml`을 한 번만 읽으므로, 마트 테이블이 추가·삭제된 경우에만 재시작하면 된다.

---

## 5. 코딩 컨벤션

- 함수·메서드에는 타입 힌트를 붙인다. 공개 API는 docstring 필수.
- 설정값은 코드에 하드코딩하지 않고 `configs/` + pydantic 모델로 주입한다.
- 부수효과(파일 쓰기, 네트워크, 주문)는 순수 계산 로직과 분리한다.
- 로깅은 `common.logging` 의 구조화 로거를 쓴다. `print()` 사용 금지.
- 매직 넘버 금지 — 의미 있는 상수/설정으로.

**dbt 레이어 규칙**

레이어 흐름: `raw → staging → intermediate → mart` (단방향, 역방향 ref 금지)

| 레이어 | 책임 | 하지 않는 것 |
|---|---|---|
| raw | `source()` 선언만. 가공 없음 | 변환 일체 |
| staging | 컬럼명 표준화·타입 캐스팅·단순 변환 (소스 1:1) | 조인, 집계 |
| intermediate | 조인·집계 등 복잡한 중간 계산. mart에만 노출, BI 직접 노출 금지 | 최종 산출물 |
| mart | 분석가·BI가 직접 쓰는 결과물. dim + fct 스타스키마 | — |

**어느 레이어에 넣을지 판단 기준**
- 컬럼명/타입만 정리 → staging
- 조인·집계가 들어가지만 최종 산출물 아님 → intermediate
- 분석가가 바로 쿼리할 결과물 → mart
- 가공 없이 원본 참조만 → source (raw)

**mart SK/FK 규칙**
- 모든 mart 테이블(dim·fct)은 `sk_id = {{ dbt_utils.generate_surrogate_key([...]) }}` 를 **첫 번째 컬럼**으로 갖는다.
  - dim: `sk_id = hash(자연 키)`. ex) `dim_security.sk_id = hash(symbol)`
  - fct: `sk_id = hash(그레인 컬럼들)`. ex) `fct_prices.sk_id = hash(date, universe, symbol)`
- fct 의 dim 참조 FK 는 `sk_dim_<테이블명>` 으로 명명한다. ex) `sk_dim_security`, `sk_dim_rate_series`
- fct 에 자연 키(series, symbol 등)와 메타(label, category 등)를 넣지 않는다 — dim 에만.
- 모든 mart parquet 은 `ORDER BY` 로 물리적 정렬을 명시한다. (DuckDB COPY TO 는 SORT 옵션 없음 → SQL ORDER BY 필수)
- `_marts_tests.yml` 에 `sk_id: [not_null, unique]` 를 반드시 포함한다.

---

## 6. ⚠️ 퀀트 도메인 안전장치 (가장 중요)

다음 규칙은 일반 코딩 규칙보다 우선합니다. 위반하면 백테스트가 거짓 성과를 내거나
실거래에서 손실로 직결됩니다.

**데이터 무결성**
- 룩어헤드 편향 금지: 시점 `t` 의 의사결정에 `t` 이후 데이터를 절대 쓰지 않는다.
- 생존편향 금지: 상장폐지·합병 종목을 포함한 point-in-time 유니버스를 사용한다.
- 미래 정보가 섞인 정규화(전체 기간 평균/표준편차 등)는 백테스트에서 금지.
  롤링/확장 윈도우만 허용.

**백테스트 현실성**
- 거래비용, 슬리피지, 시장 충격, 체결 지연을 반드시 반영한다. 무비용 백테스트 결과는
  제출하지 않는다.
- 파라미터 과최적화(overfitting) 경계 — 워크포워드/교차검증 없이 단일 기간 튜닝 결과를
  성과로 보고하지 않는다.

**금융 계산**
- 가격·수량·금액 등 정밀도가 중요한 값은 `float` 누적 오차에 주의한다. 필요 시
  `Decimal` 또는 정수(최소단위) 사용.
- 수익률 계산 시 로그/단순 수익률을 혼용하지 말 것. 컨벤션을 명시한다.

**실거래(라이브) 가드레일**
- 실제 주문을 내는 코드(`execution/` 의 라이브 경로)는 **사용자의 명시적 확인 없이
  작성·수정·실행하지 않는다.**
- 모든 라이브 집행은 `risk/` 의 사전 한도 체크(포지션 한도, 노출 한도, 킬 스위치)를
  반드시 통과해야 한다.
- 기본값은 dry-run / paper trading. 실거래 활성화는 명시적 설정 플래그로만.

**비밀정보 / 보안**
- API 키, 시크릿, 계좌 정보를 코드·로그·커밋에 절대 노출하지 않는다.
  환경변수 또는 시크릿 매니저에서 로드한다.
- `data/`, `.env`, 자격증명 파일은 절대 커밋하지 않는다 (`.gitignore` 확인).

**재현성**
- 난수를 쓰는 모든 곳에 시드를 고정한다.
- 백테스트 결과에는 사용한 데이터 버전/스냅샷과 설정을 함께 기록한다.

---

## 7. 테스트 요구사항

- 새 시그널·전략·최적화 로직에는 테스트를 동반한다.
- 데이터 변환에는 룩어헤드/시점 정확성 검증 테스트를 포함한다.
- 외부 의존(거래소 API, 데이터 벤더)은 테스트에서 모킹한다 — 실거래/실호출 금지.

---

## 8. Git / PR

- 커밋 메시지: `<타입>: <요약>` (예: `feat: 모멘텀 팩터 추가`, `fix: PIT 정렬 버그`)
- PR 전 체크리스트: 테스트 통과 / 린트·타입 통과 / 데이터·시크릿 미포함 확인.
- 큰 변경은 레이어 단위로 분리해 작은 PR로.

---

## 9. 하지 말아야 할 것 (요약)

- ❌ `data/` 나 시크릿 커밋
- ❌ 룩어헤드·생존편향이 들어간 백테스트
- ❌ 거래비용 없는 성과 보고
- ❌ 명시적 확인 없는 라이브 주문 코드 작성/실행
- ❌ `notebooks/` 에 운영 로직 작성
- ❌ 레이어 간 역방향 의존

---

## 10. 한국 시장 데이터 파이프라인 — 소스 아키텍처

### 10-1. 확정된 소스 테이블

| 데이터 | 1차 소스 | 비고 |
|---|---|---|
| 종목 OHLCV (일/분봉) | **KIS REST** (한국투자증권) | REST·토큰인증·무료·합법 |
| 기관/외국인 종목별 수급 | **KIS REST** | 증권사 경유, KRX 원본과 미세차이 가능 |
| 실시간 시세 (intraday) | **KIS WebSocket** | 5분봉 수집과 연동 |
| 프로그램매매 흐름 | **KIS REST 시세분석 계열** | 장기 히스토리·차익/비차익 세부는 약함 |
| 금리·거시·환율 | **FRED** (FDR 경유) | 안정적, 검증됨 |
| 한국 거시 (CPI 등) | **ECOS** (한국은행) | rate limit 엄격, throttle 필수 |
| VKOSPI | 네이버 보조 스크래핑 | best-effort, 메인 의존 금지 |
| 시장 전체 통계 (ADR 등) | 보조 스크래핑 / 유료벤더 | |

### 10-2. ⚠️ KRX 접근 금지 사항 (재조사·재시도 금지)

- **2025-12-27**: KRX 정보데이터시스템 회원제 전환, 로그인 필수화.
- **2026-05-21** (`v=20260521_1`): `dbms/MDC/STAT/standard/*` 전체 로그인 인증 추가.
  - 영향: 투자자별 매매동향, VKOSPI, 프로그램매매, ADR 등 **STAT 통계 전체 차단**.
  - 무인증 호출 → 응답 본문 `LOGOUT` (HTTP 400).
  - `mdc.util.js` 에서 확인: `jqXHR.responseText === 'LOGOUT'` → 로그인 페이지 강제 이동.
- `dbms/comm/finder/*` (단순 종목 검색 등)는 **여전히 무인증** 가능.
- **pykrx 통계 함수 전면 사용 금지.** 내부 `KrxWebIo` → JSON 파싱 실패 → 빈 DataFrame.
- KRX는 비공식 과도 접속에 **IP 영구 차단** (해제 불가 공식 입장). finder 외 KRX 직접 호출 금지.

### 10-3. 작동 확인된 소스 (그대로 신뢰)

- **FRED 경유**: `IRLTLT01KRM156N` (한국 10Y 국채), `KORCPIALLMINMEI`, 수출입 금액 YoY 정상.
- **ECOS**: 정상이나 3분간 300회 초과 시 30분 차단(`ERROR-602`). 보수적 throttle 필수.
- **Yahoo Finance**: KOSPI = `^KS11`, KOSDAQ = `^KQ11`. `.KS`/`.KQ` 접미사·`^VKOSPI` = 404. 재시도 금지.

### 10-4. 확정된 설계 결정 (사용자 답변 기반)

- **유니버스**: KOSPI200 구성종목 (PIT 이력 포함)
- **수집 주기**: 실시간(KIS WebSocket intraday) + 장마감 후 배치(EOD) 병행
- **프로그램매매 용도**: 모델 학습 및 신호용 — 과거 시계열 깊이 확보 필요
- **저장소**: intraday DB와 EOD daily DB 분리
- **KIS 인증**: APP_KEY/SECRET 미발급 → 발급 후 `.env` 에서 로드

### 10-5. 구현 규칙

- 모든 외부 호출에 throttle + 지수 백오프. ECOS는 특히 보수적으로 (호출 간 최소 1초).
- KIS 접근 토큰은 만료 전까지 파일/메모리 캐시 재사용. 매 호출 재발급 금지.
- 비공식 스크래핑(네이버 등)은 별도 모듈로 격리. 실패해도 전체 파이프라인 중단 금지.
- 멱등성: 재실행 시 중복 적재 방지 (upsert 또는 기간 체크).
- KIS APP_KEY / ECOS KEY / 계좌번호는 환경변수 또는 `.env` 에서만 로드. 코드 하드코딩 금지.
