---
title: 매크로
---

FX·달러인덱스·원자재·지수·크레딧·인플레이션 시계열. `dim_macro_series` 조인으로 label/category/source 보강.

```sql latest
select
  d.category, d.label, d.unit, d.source,
  max(f.date)                             as latest_date,
  last(f.value order by f.date)           as latest_value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
group by all
order by d.category, d.label
```

<DataTable data={latest} rows=30/>

---

## FX

```sql fx
select f.date, d.label, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'fx'
order by f.date
```

<LineChart data={fx} x=date y=value series=label title="FX" yAxisTitle="값"/>

---

## 달러인덱스 (DXY)

```sql dxy
select f.date, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.label = '달러인덱스 DXY'
order by f.date
```

<LineChart data={dxy} x=date y=value title="달러인덱스 DXY" yAxisTitle="index"/>

---

## 변동성 — VIX

```sql vix
select f.date, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.label = 'VIX 변동성 지수'
order by f.date
```

<LineChart data={vix} x=date y=value title="VIX (공포 지수)" yAxisTitle="index"/>

---

## 크레딧 스프레드 — HY / IG OAS

```sql credit
select f.date, d.label, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'credit'
order by f.date
```

<LineChart data={credit} x=date y=value series=label title="크레딧 스프레드 (OAS)" yAxisTitle="%"/>

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

## 원자재

```sql commodity
select f.date, d.label, d.unit, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'commodity'
order by f.date
```

<LineChart data={commodity} x=date y=value series=label title="원자재" yAxisTitle="USD"/>

---

## 한국 수출입 증감률 YoY

```sql trade
select f.date, d.label, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'trade'
order by f.date
```

<LineChart data={trade} x=date y=value series=label title="한국 수출입 YoY (%)" yAxisTitle="%"/>

---

## 인플레이션 / 매크로 지표

```sql inflation
select f.date, d.label, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.category = 'macro' and d.label in ('미국 CPI', '미국 PCE', '미국 10Y 기대인플레이션', '미국 5y5y 기대인플레이션')
order by f.date
```

<LineChart data={inflation} x=date y=value series=label title="인플레이션 지표" yAxisTitle="index / %"/>

---

## 고용 — NFP · 실업수당청구

```sql employment
select f.date, d.label, d.unit, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.label in ('미국 비농업 고용(NFP)', '미국 실업수당청구')
order by f.date
```

<LineChart data={employment} x=date y=value series=label title="고용 지표" yAxisTitle="thousands"/>

---

## 통화량 · 연준 대차대조표 (미국)

```sql monetary
select f.date, d.label, d.unit, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.label in ('미국 M2', '연준 대차대조표')
order by f.date
```

<LineChart data={monetary} x=date y=value series=label title="미국 통화량 · 연준 대차대조표"/>

---

## 한국 M2 (광의통화)

```sql kr_m2
select f.date, f.value
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.label = '한국 M2 (광의통화 평잔)'
order by f.date
```

<LineChart data={kr_m2} x=date y=value title="한국 M2 (광의통화 평잔)" yAxisTitle="십억원" colorPalette={["#e85d04"]}/>

---

## 시리즈별 조회

```sql series_meta
select series, label, unit, category, source from quant.macro_series order by category, series
```

<Dropdown data={series_meta} name=sel value=label label=label/>

```sql one
select f.date, f.value, d.label, d.unit, d.source, d.category
from quant.macro f
join quant.macro_series d on f.sk_dim_macro_series = d.sk_id
where d.label = '${inputs.sel.value}'
order by f.date
```

**{one[0].label}** ({one[0].unit}) | 소스: {one[0].source} | 카테고리: {one[0].category}

<LineChart data={one} x=date y=value yAxisTitle="{one[0].unit}"/>

<DataTable data={one} rows=10/>
