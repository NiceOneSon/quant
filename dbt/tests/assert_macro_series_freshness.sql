-- 시리즈별 발표 주기(frequency)에 따라 max(date)가 너무 오래됐는지 검증.
-- 실패 시: 지연된 시리즈 목록과 마지막 날짜, 경과 일수를 출력.
--
-- 임계값 (error 기준):
--   daily   → 10일 초과 (EIA/FRED 에너지 스팟 가격은 주말 포함 최대 8일 지연)
--   weekly  → 14일 초과
--   monthly → 120일 초과 (FRED 월별 시리즈 발표 lag 최대 3개월 이상 감안)
with last_dates as (
    select
        d.series,
        d.label,
        d.frequency,
        max(f.date) as last_date,
        current_date - max(f.date) as days_since
    from {{ ref('dim_macro_series') }} d
    join {{ ref('fct_macro') }} f on d.sk_id = f.sk_dim_macro_series
    group by d.series, d.label, d.frequency
),
thresholds as (
    select
        series,
        label,
        frequency,
        last_date,
        days_since,
        case frequency
            when 'daily'   then 10
            when 'weekly'  then 14
            when 'monthly' then 120
            else 120
        end as error_after_days
    from last_dates
)
select series, label, frequency, last_date, days_since, error_after_days
from thresholds
where days_since > error_after_days
