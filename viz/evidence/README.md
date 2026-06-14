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

## 작성 규칙

- **Dropdown `value`는 항상 `label` 또는 `name` 필드를 사용한다. 시리즈 코드·종목 코드를 value나 defaultValue로 쓰지 않는다.**
  - 잘못된 예: `value=series defaultValue="IR3TIB01KRM156N"`
  - 올바른 예: `value=label label=label`
- **`defaultValue`는 사용하지 않는다** — Evidence가 데이터 첫 번째 행을 자동 선택한다.
- **쿼리 필터도 label/name 기준으로 작성한다.** 드롭다운 뿐 아니라 내부 분석 쿼리(스프레드 계산, KPI 등)도 마찬가지다.
  - 잘못된 예: `where d.series = 'DGS10'`
  - 올바른 예: `where d.label = '미국채 10년'`

## Docker (프로덕션)

```bash
docker compose up -d --build   # Evidence(3000) + DuckDB UI(4213)
docker compose down
```
