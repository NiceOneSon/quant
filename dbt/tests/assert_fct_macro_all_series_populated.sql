-- dim_macro_series(seed)에 등록된 모든 시리즈가 fct_macro에 데이터가 있는지 검증.
-- 실패 시: seed에는 있지만 수집(ingest)이 안 된 시리즈 목록이 출력됨.
select d.series
from {{ ref('dim_macro_series') }} d
left join {{ ref('fct_macro') }} f on d.sk_id = f.sk_dim_macro_series
where f.sk_id is null
