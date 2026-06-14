---
title: Quant 대시보드
---

`data/` 의 parquet(가격·금리·유니버스)을 DuckDB 로 읽어 시각화합니다.

```sql kpi
select
  count(distinct symbol) as symbols,
  count(*) as n_rows,
  max(date) as latest
from quant.prices
```

```sql kpi_uni
select count(*) as members from quant.universe
```

```sql kpi_rf
select rate from quant.rates order by date desc limit 1
```

<BigValue data={kpi} value=symbols title="가격 종목 수"/>
<BigValue data={kpi} value=latest title="최신 거래일"/>
<BigValue data={kpi_uni} value=members title="유니버스 멤버십"/>
<BigValue data={kpi_rf} value=rate title="무위험금리(%)"/>

## 페이지

- [가격](/prices) — 종목별 OHLCV·거래량
- [유니버스](/universe) — 구성 종목·소스별 규모
- [금리](/rates) — 무위험금리 추이
