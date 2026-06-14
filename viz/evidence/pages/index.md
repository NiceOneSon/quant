---
title: Quant 대시보드
---

`data/marts/` parquet(가격·금리·매크로·유니버스)을 DuckDB 로 읽어 시각화합니다.

```sql kpi
select
  count(distinct symbol) as symbols,
  count(*)               as n_rows,
  max(date)              as latest
from quant.prices
```

```sql kpi_uni
select count(*) as members from quant.universe
```

```sql kpi_rf
select rate
from quant.rates
where series = 'IR3TIB01KRM156N'
order by date desc
limit 1
```

```sql kpi_macro
select
  max(case when series = 'USD/KRW'  then value end) as usdkrw,
  max(case when series = 'KS11'     then value end) as kospi
from quant.macro
where date = (select max(date) from quant.macro)
```

<BigValue data={kpi} value=symbols title="가격 종목 수"/>
<BigValue data={kpi} value=latest title="최신 거래일"/>
<BigValue data={kpi_uni} value=members title="유니버스 멤버십"/>
<BigValue data={kpi_rf} value=rate title="한국 3M 금리(%)"/>
<BigValue data={kpi_macro} value=usdkrw title="USD/KRW"/>
<BigValue data={kpi_macro} value=kospi title="KOSPI"/>

## 페이지

- [가격](/prices) — 종목별 OHLCV·거래량·거래정지
- [유니버스](/universe) — 구성 종목·소스별 규모
- [금리](/rates) — 무위험금리·국채 수익률 곡선
- [매크로](/macro) — FX·달러인덱스·원자재·지수
