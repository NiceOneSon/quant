# Evidence 대시보드

dbt 마트 parquet(`data/marts/`)을 소스로 하는 코드형 BI 대시보드.

## 페이지

| 경로 | 내용 |
|---|---|
| `/prices` | 종목별 수정주가 OHLCV·거래량. 유니버스·종목 드롭다운 필터 |
| `/rates` | 무위험금리·국채 수익률 곡선·장단기 스프레드 (KR/US) |
| `/macro` | FX·달러인덱스·VIX·원자재·크레딧·인플레이션·고용·통화량·수출입 |
| `/universe` | 유니버스 편입·편출 이력 (valid_from / valid_to) |

## 로컬 개발 (핫리로드)

```bash
cd viz/evidence
npm install
npm run sources    # dbt 마트 parquet → Evidence 소스 캐시
npm run dev        # http://localhost:3000
```

## dbt 변경 후 필수 순서

```bash
make dbt-build                      # 1) 마트 재생성 + Evidence 캐시 클리어
cd viz/evidence && npm run sources  # 2) 소스 재빌드
```

> Evidence 소스(`npm run sources`)는 캐시 클리어 후 반드시 재실행해야 한다.
> 누락 시 페이지가 오래된 parquet을 참조하거나 ENOENT 오류가 발생한다.

## 작성 규칙 — 내부 코드 노출 금지

UI에서 `series`, `symbol`, `universe` 같은 내부 식별자 코드가 보이면 안 된다.
**name / label 만 노출한다.** 아래 세 레이어 모두에서 일관되게 적용한다.

### 1. 소스 SQL (`sources/quant/*.sql`)

`select *` 대신 컬럼을 명시해 내부 코드 컬럼을 제외한다.

| 소스 파일 | 제외 컬럼 | 노출 컬럼 |
|---|---|---|
| `rate_series.sql` | `series` | `sk_id, label, country, tenor` |
| `macro_series.sql` | `series` | `sk_id, label, unit, country, category, source, frequency` |
| `security.sql` | `symbol` | `sk_id, name, market` |
| `universe.sql` | `universe` (코드) | `sk_id, universe_name, symbol→name, valid_from, valid_to, is_current` |

새 소스 추가 시: `select *` 금지. SK(`sk_id`)와 사람이 읽을 수 있는 컬럼만 노출.

### 2. 페이지 쿼리 (`pages/*.md`)

- SELECT에 코드 컬럼을 포함하지 않는다.
  - 잘못된 예: `select d.series, d.label, ...`
  - 올바른 예: `select d.label, d.country, d.tenor, ...`
- WHERE 필터도 label/name 기준으로 작성한다.
  - 잘못된 예: `where d.series = 'IR3TIB01KRM156N'`
  - 올바른 예: `where d.label = '한국 3개월 은행간'`
- ORDER BY도 마찬가지.
  - 잘못된 예: `order by d.series`
  - 올바른 예: `order by d.label`

### 3. 드롭다운 컴포넌트

- `value`는 반드시 `label` 또는 `name` 필드를 사용한다.
  - 잘못된 예: `value=series defaultValue="IR3TIB01KRM156N"`
  - 올바른 예: `value=label label=label`
- `defaultValue`는 사용하지 않는다 — Evidence가 첫 번째 행을 자동 선택한다.

### 새 유니버스/시리즈 추가 시 체크리스트

- [ ] `dim_universe_history.sql` CASE WHEN에 `universe_name` 매핑 추가
- [ ] `rate_series` / `macro_series` seed에 `label` 컬럼 입력
- [ ] 소스 SQL의 명시적 컬럼 목록에 새 컬럼이 필요하면 추가 (코드 컬럼은 제외 유지)

## Docker (프로덕션)

```bash
docker compose up -d --build   # Evidence(3000) + DuckDB UI(4213)
docker compose down
```
