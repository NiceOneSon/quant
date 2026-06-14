---
title: 금리
---

무위험금리·국채 수익률. `dim_rate_series` 조인으로 label/country 보강.

## 미국 국채 수익률 곡선 (3M / 2Y / 10Y)

```sql us_curve
select f.date, d.label, f.rate
from quant.rates f
join quant.rate_series d on f.sk_dim_rate_series = d.sk_id
where d.country = 'US' and d.tenor in ('3M', '2Y', '10Y')
order by f.date
```

<LineChart data={us_curve} x=date y=rate series=label yAxisTitle="%"/>

## 장단기 스프레드 (10Y − 2Y) — 음수면 수익률곡선 역전(침체 신호)

```sql spread
select a.date, a.rate - b.rate as spread_10y_2y
from quant.rates a
join quant.rate_series da on a.sk_dim_rate_series = da.sk_id
join quant.rates b      on a.date = b.date
join quant.rate_series db on b.sk_dim_rate_series = db.sk_id
where da.series = 'DGS10' and db.series = 'DGS2'
order by a.date
```

<LineChart data={spread} x=date y=spread_10y_2y yAxisTitle="%p"/>

## 시리즈별 조회

```sql series_list
select d.series, d.label, d.country, d.tenor
from quant.rate_series d
order by d.country, d.tenor
```

<Dropdown data={series_list} name=sel value=series label=label defaultValue="IR3TIB01KRM156N"/>

```sql one
select f.date, d.label, d.country, d.tenor, f.rate
from quant.rates f
join quant.rate_series d on f.sk_dim_rate_series = d.sk_id
where d.series = '${inputs.sel.value}'
order by f.date
```

<LineChart data={one} x=date y=rate yAxisTitle="%"/>

<DataTable data={one} rows=10/>
