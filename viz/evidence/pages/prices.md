---
title: 가격
---

수정주가 OHLCV. 유니버스·종목을 선택하세요.

```sql universes
select distinct u.universe
from quant.prices p
join quant.universe u on p.sk_dim_universe_history = u.sk_id
order by u.universe
```

<Dropdown data={universes} name=univ value=universe label=universe/>

```sql symbols
select u.symbol, s.name, u.symbol || ' ' || s.name as label
from quant.prices p
join quant.universe u on p.sk_dim_universe_history = u.sk_id
join quant.security s on u.symbol = s.symbol
where u.universe = '${inputs.univ.value}'
group by u.symbol, s.name
order by u.symbol
```

<Dropdown data={symbols} name=sym value=symbol label=label/>

```sql series
select p.date, p.open, p.high, p.low, p.close, p.volume, p.is_halted
from quant.prices p
join quant.universe u on p.sk_dim_universe_history = u.sk_id
where u.universe = '${inputs.univ.value}'
  and u.symbol = '${inputs.sym.value}'
order by p.date
```

## 종가 (수정주가)

<LineChart data={series} x=date y=close yAxisTitle="KRW"/>

## 거래량

<BarChart data={series} x=date y=volume/>

## 최근 10거래일

```sql recent
select p.date, p.open, p.high, p.low, p.close, p.volume, p.is_halted
from quant.prices p
join quant.universe u on p.sk_dim_universe_history = u.sk_id
where u.universe = '${inputs.univ.value}'
  and u.symbol = '${inputs.sym.value}'
order by p.date desc
limit 10
```

<DataTable data={recent}/>
