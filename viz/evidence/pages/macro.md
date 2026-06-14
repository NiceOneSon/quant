---
title: 매크로
---

FX·달러인덱스·원자재·지수 시계열. `dim_macro_series` 조인으로 label/category 보강.

```sql latest
select
  d.series, d.label, d.unit, d.category,
  max(f.date)                             as latest_date,
  last(f.value order by f.date)           as latest_value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
group by all
order by d.category, d.series
```

<DataTable data={latest} rows=20/>

---

## FX — 달러-원 / 달러-엔

```sql fx
select f.date, d.label, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'fx'
order by f.date
```

<LineChart data={fx} x=date y=value series=label title="FX (달러-원 / 달러-엔)" yAxisTitle="값"/>

---

## 달러인덱스 (DXY)

```sql dxy
select f.date, f.value
from quant.macro f
where f.series = 'DTWEXBGS'
order by f.date
```

<LineChart data={dxy} x=date y=value title="달러인덱스 DXY" yAxisTitle="index"/>

---

## 국내 주요 지수

```sql indices
select f.date, d.label, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'index'
order by f.date
```

<LineChart data={indices} x=date y=value series=label title="KOSPI / KOSPI200 / KOSDAQ" yAxisTitle="point"/>

---

## 원자재 — WTI · 구리

```sql commodity
select f.date, d.label, d.unit, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'commodity'
order by f.date
```

<LineChart data={commodity} x=date y=value series=label title="원자재" yAxisTitle="USD"/>

---

## 시리즈별 조회

```sql series_meta
select series, label, unit, category from quant.macro_series order by category, series
```

<Dropdown data={series_meta} name=sel value=series label=label defaultValue="USD/KRW"/>

```sql one
select f.date, f.value, d.label, d.unit
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where f.series = '${inputs.sel.value}'
order by f.date
```

**{inputs.sel.value}** — {one[0].label} ({one[0].unit})

<LineChart data={one} x=date y=value yAxisTitle="{one[0].unit}"/>

<DataTable data={one} rows=10/>
