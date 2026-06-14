---
title: 유니버스
---

유니버스별 편입·편출 이력. `valid_to = null` 이면 현재 편입 중.

```sql by_universe
select universe, count(*) as members
from quant.universe
where is_current = true
group by universe
order by members desc
```

## 유니버스별 현재 편입 종목 수

<BarChart data={by_universe} x=universe y=members swapXY=true/>

## 현재 편입 종목 목록

```sql members
select universe, symbol, name, valid_from
from quant.universe
where is_current = true
order by universe, name
```

<DataTable data={members} rows=15 search=true/>

## 멤버십 이력 전체

```sql history
select universe, symbol, name, valid_from, valid_to, is_current
from quant.universe
order by universe, name, valid_from
```

<DataTable data={history} rows=15 search=true/>
