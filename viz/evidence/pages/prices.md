---
title: 가격
---

kospi40 종목의 수정주가 OHLCV. 종목을 선택하세요.

```sql symbols
select distinct symbol
from quant.prices
where universe = 'kospi40'
order by symbol
```

<Dropdown data={symbols} name=symbol value=symbol defaultValue="005930"/>

```sql series
select date, open, high, low, close, volume
from quant.prices
where symbol = '${inputs.symbol.value}' and universe = 'kospi40'
order by date
```

## 종가 (수정주가)

<LineChart data={series} x=date y=close yAxisTitle="KRW"/>

## 거래량

<BarChart data={series} x=date y=volume/>

## 최근 10거래일

```sql recent
select date, open, high, low, close, volume
from quant.prices
where symbol = '${inputs.symbol.value}' and universe = 'kospi40'
order by date desc
limit 10
```

<DataTable data={recent}/>
