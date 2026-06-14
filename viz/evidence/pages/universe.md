---
title: 유니버스
---

point-in-time 유니버스 멤버십. 소스 파일별 규모와 종목 목록.

```sql by_source
select filename, count(*) as members
from quant.universe
group by filename
order by members desc
```

## 소스 파일별 구성 종목 수

<BarChart data={by_source} x=filename y=members swapXY=true/>

## 멤버십 목록

```sql members
select symbol, added, removed, filename
from quant.universe
order by filename, symbol
```

<DataTable data={members} rows=15 search=true/>
