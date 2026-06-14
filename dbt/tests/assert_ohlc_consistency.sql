-- Singular test: OHLC 가격 일관성.
-- 실패 조건: 고가 < 저가, 또는 고가 < 시·종가, 또는 저가 > 시·종가.
-- 이 테스트 실패 = 소스 데이터 오류 (수집·정제 버그 가능성).
select
    universe,
    symbol,
    date,
    open,
    high,
    low,
    close
from {{ ref('fct_prices') }}
where
    high < low      -- 고가가 저가보다 낮음 (불가능)
    or high < open  -- 고가가 시가보다 낮음
    or high < close -- 고가가 종가보다 낮음
    or low  > open  -- 저가가 시가보다 높음
    or low  > close -- 저가가 종가보다 높음
