---
title: 금리
---

무위험금리·국채 수익률. `dim_rate_series` 조인으로 label/country/tenor 보강.

## 미국 국채 수익률 곡선 (3M / 2Y / 10Y)

```sql us_curve
select f.date, d.label, f.rate
from quant.rates f
join quant.rate_series d on f.sk_dim_rate_series = d.sk_id
where d.country = 'US' and d.tenor in ('3M', '2Y', '10Y')
order by f.date
```

<LineChart data={us_curve} x=date y=rate series=label yAxisTitle="%"/>

---

## 장단기 스프레드 (10Y − 2Y) — 음수면 수익률곡선 역전(침체 신호)

```sql spread
select a.date, a.rate - b.rate as spread_10y_2y
from quant.rates a
join quant.rate_series da on a.sk_dim_rate_series = da.sk_id
join quant.rates b      on a.date = b.date
join quant.rate_series db on b.sk_dim_rate_series = db.sk_id
where da.label = '미국채 10년' and db.label = '미국채 2년'
order by a.date
```

<LineChart data={spread} x=date y=spread_10y_2y yAxisTitle="%p"/>

---

## 정책금리 — Fed Funds vs SOFR

```sql policy
select f.date, d.label, f.rate
from quant.rates f
join quant.rate_series d on f.sk_dim_rate_series = d.sk_id
where d.label in ('미 연방기금금리', 'SOFR (미국 익일 담보부)')
order by f.date
```

<LineChart data={policy} x=date y=rate series=label title="정책금리 / SOFR" yAxisTitle="%"/>

---

## 국가별 전체 시리즈

```sql all_series
select f.date, d.label, d.country, f.rate
from quant.rates f
join quant.rate_series d on f.sk_dim_rate_series = d.sk_id
order by d.country, d.tenor, f.date
```

<LineChart data={all_series} x=date y=rate series=label title="전체 금리 시리즈" yAxisTitle="%"/>

---

## 시리즈별 조회

```sql series_list
select d.label, d.country, d.tenor
from quant.rate_series d
order by d.country, d.tenor
```

<Dropdown data={series_list} name=sel value=label label=label/>

```sql one
select f.date, d.label, d.country, d.tenor, f.rate
from quant.rates f
join quant.rate_series d on f.sk_dim_rate_series = d.sk_id
where d.label = '${inputs.sel.value}'
order by f.date
```

<LineChart data={one} x=date y=rate yAxisTitle="%"/>

<DataTable data={one} rows=10/>
