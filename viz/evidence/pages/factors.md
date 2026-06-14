---
title: 팩터 스코어
---

종목 단면 팩터(Momentum / Low-vol / Liquidity) 랭킹. 롱온리 바스켓 구성 기준.

```sql latest_date
select max(date) as dt from quant.stock_features
```

```sql universes
select distinct universe_name from quant.stock_features order by universe_name
```

<Dropdown data={universes} name=univ value=universe_name label=universe_name/>

---

## 최신 종합 랭킹

```sql ranking
select
    name,
    round(score_composite, 3) as score_composite,
    round(score_mom,        3) as score_mom,
    round(score_lowvol,     3) as score_lowvol,
    round(score_liq,        3) as score_liq,
    round(mom_12_1m * 100,  1) as mom_12_1m_pct,
    round(vol_1m * 100,     2) as vol_1m_pct,
    round(beta_1y,          2) as beta_1y,
    round(adv_20d / 1e8,    1) as adv_20d_억원
from quant.stock_features
where universe_name = '${inputs.univ.value}'
  and date = (select max(date) from quant.stock_features)
order by score_composite desc
```

<BarChart
    data={ranking}
    x=name
    y=score_composite
    swapXY=true
    title="종합 스코어 (높을수록 우위)"
    yMin=0 yMax=1
/>

<DataTable data={ranking} rows=20 search=true/>

---

## 팩터 패밀리별 스코어 분포

```sql family_dist
select
    name,
    score_mom    as 모멘텀,
    score_lowvol as 저변동성,
    score_liq    as 유동성
from quant.stock_features
where universe_name = '${inputs.univ.value}'
  and date = (select max(date) from quant.stock_features)
order by score_composite desc
limit 20
```

<BarChart
    data={family_dist}
    x=name
    y={['모멘텀', '저변동성', '유동성']}
    swapXY=true
    type=grouped
    title="패밀리 스코어 상위 20 (최신일)"
/>

---

## 종목별 팩터 이력

```sql stock_list
select distinct name from quant.stock_features
where universe_name = '${inputs.univ.value}'
order by name
```

<Dropdown data={stock_list} name=stk value=name label=name/>

```sql stock_scores
select date, score_composite, score_mom, score_lowvol, score_liq
from quant.stock_features
where universe_name = '${inputs.univ.value}'
  and name = '${inputs.stk.value}'
order by date
```

<LineChart
    data={stock_scores}
    x=date
    y={['score_composite', 'score_mom', 'score_lowvol', 'score_liq']}
    title="{inputs.stk.value} — 팩터 스코어 추이"
    yMin=0 yMax=1
/>

```sql stock_raw
select
    date,
    round(mom_12_1m * 100, 1) as mom_12_1m_pct,
    round(mom_6m    * 100, 1) as mom_6m_pct,
    round(mom_1m    * 100, 1) as mom_1m_pct,
    round(vol_1m    * 100, 2) as vol_1m_pct,
    round(vol_3m    * 100, 2) as vol_3m_pct,
    round(beta_1y,          2) as beta_1y,
    round(adv_20d / 1e8,    1) as adv_20d_억원
from quant.stock_features
where universe_name = '${inputs.univ.value}'
  and name = '${inputs.stk.value}'
order by date desc
limit 30
```

<DataTable data={stock_raw} rows=10/>
