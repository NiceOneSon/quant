---
title: 매크로
---

FX·달러인덱스·원자재·지수 시계열. `fct_macro` 마트 기준.

```sql latest
select
  series,
  label,
  unit,
  category,
  max(date)   as latest_date,
  last(value order by date) as latest_value
from quant.macro
group by all
order by category, series
```

<DataTable data={latest} rows=20/>

---

## FX — 달러-원 / 달러-엔

```sql fx
select date, series, label, value
from quant.macro
where category = 'fx'
order by date
```

<LineChart
  data={fx}
  x=date
  y=value
  series=label
  title="FX (달러-원 / 달러-엔)"
  yAxisTitle="값"
/>

---

## 달러인덱스 (DXY)

```sql dxy
select date, value
from quant.macro
where series = 'DTWEXBGS'
order by date
```

<LineChart
  data={dxy}
  x=date
  y=value
  title="달러인덱스 DXY (DTWEXBGS)"
  yAxisTitle="index"
/>

---

## 국내 주요 지수

```sql indices
select date, series, label, value
from quant.macro
where category = 'index'
order by date
```

<LineChart
  data={indices}
  x=date
  y=value
  series=label
  title="KOSPI / KOSPI200 / KOSDAQ"
  yAxisTitle="point"
/>

---

## 원자재 — WTI · 구리

```sql commodity
select date, series, label, unit, value
from quant.macro
where category = 'commodity'
order by date
```

<LineChart
  data={commodity}
  x=date
  y=value
  series=label
  title="원자재"
  yAxisTitle="USD"
/>

---

## 시리즈별 조회

```sql series_meta
select distinct series, label, unit, category
from quant.macro
order by category, series
```

<Dropdown data={series_meta} name=sel value=series label=label defaultValue="USD/KRW"/>

```sql one
select date, value, label, unit
from quant.macro
where series = '${inputs.sel.value}'
order by date
```

**{inputs.sel.value}** — {one[0].label} ({one[0].unit})

<LineChart data={one} x=date y=value yAxisTitle="{one[0].unit}"/>

<DataTable data={one} rows=10/>
