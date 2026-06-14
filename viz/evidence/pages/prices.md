---
title: 가격
---

kospi40 종목의 수정주가 OHLCV. 종목을 선택하세요.

```sql symbols
select p.symbol, s.name, p.symbol || ' ' || s.name as label
from (select distinct symbol from quant.prices where universe = 'kospi40') p
join quant.security s on p.symbol = s.symbol
order by p.symbol
```

<Dropdown data={symbols} name=sym value=symbol label=label defaultValue="005930"/>

```sql series
select date, open, high, low, close, volume, is_halted
from quant.prices
where symbol = '${inputs.sym.value}' and universe = 'kospi40'
order by date
```

## 종가 (수정주가)

<LineChart data={series} x=date y=close yAxisTitle="KRW"/>

## 거래량

<BarChart data={series} x=date y=volume/>

## 최근 10거래일

```sql recent
select date, open, high, low, close, volume, is_halted
from quant.prices
where symbol = '${inputs.sym.value}' and universe = 'kospi40'
order by date desc
limit 10
```

<DataTable data={recent}/>
