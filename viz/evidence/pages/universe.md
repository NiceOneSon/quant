---
title: 유니버스
---

point-in-time 유니버스 멤버십 이력 (SCD2). 실제 편입 구간(`is_member=true`)과 갭 구간(`is_member=false`)을 모두 포함한다.

```sql by_source
select universe, count(*) as members
from quant.universe
where is_member = true
group by universe
order by members desc
```

## 유니버스별 현재 편입 종목 수

<BarChart data={by_source} x=universe y=members swapXY=true/>

## 멤버십 목록

```sql members
select universe, symbol, valid_from, valid_to, is_current
from quant.universe
where is_member = true
order by universe, symbol
```

<DataTable data={members} rows=15 search=true/>

## 편입/편출 이력 전체 (갭 구간 포함)

```sql history
select universe, symbol, valid_from, valid_to, is_member, is_current
from quant.universe
order by universe, symbol, valid_from
```

<DataTable data={history} rows=15 search=true/>
