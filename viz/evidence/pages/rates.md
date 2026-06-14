---
title: 금리
---

무위험금리·국채 수익률. `country`(KR/US)·`series` 로 구분.

## 미국 국채 수익률 곡선 (3M / 2Y / 10Y)

```sql us_curve
select date, series, rate
from quant.rates
where country = 'US' and series in ('DGS3MO', 'DGS2', 'DGS10')
order by date
```

<LineChart data={us_curve} x=date y=rate series=series yAxisTitle="%"/>

## 장단기 스프레드 (10Y − 2Y) — 음수면 수익률곡선 역전(침체 신호)

```sql spread
select a.date, a.rate - b.rate as spread_10y_2y
from (select date, rate from quant.rates where series = 'DGS10') a
join (select date, rate from quant.rates where series = 'DGS2') b using (date)
order by a.date
```

<LineChart data={spread} x=date y=spread_10y_2y yAxisTitle="%p"/>

## 시리즈별 조회

```sql series_list
select distinct country, series from quant.rates order by country, series
```

<Dropdown data={series_list} name=series value=series defaultValue="IR3TIB01KRM156N"/>

```sql one
select date, country, series, rate
from quant.rates
where series = '${inputs.series.value}'
order by date
```

<LineChart data={one} x=date y=rate yAxisTitle="%"/>

<DataTable data={one} rows=10/>
