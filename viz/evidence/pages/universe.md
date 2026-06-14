---
title: 유니버스
---

point-in-time 유니버스 멤버십. 소스 파일별 규모와 종목 목록.

```sql by_source
select universe, count(*) as members
from quant.universe
group by universe
order by members desc
```

## 유니버스별 구성 종목 수

<BarChart data={by_source} x=universe y=members swapXY=true/>

## 멤버십 목록

```sql members
select universe, symbol, added, removed
from quant.universe
order by universe, symbol
```

<DataTable data={members} rows=15 search=true/>
