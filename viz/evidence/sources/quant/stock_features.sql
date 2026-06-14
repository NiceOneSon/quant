-- fct_stock_features: 종목 단면 팩터.
-- dim_universe_history 조인으로 name·universe_name 보강 (dim_security 불필요).
select
    f.date,
    u.name,
    u.universe_name,
    f.mom_1m, f.mom_6m, f.mom_12_1m, f.rev_1w, f.hi52w_ratio,
    f.vol_1m, f.vol_3m, f.beta_1y, f.idio_vol_1m,
    f.adv_20d, f.vol_surge,
    f.mom_12_1m_rank, f.mom_6m_rank, f.mom_1m_rank, f.rev_1w_rank, f.hi52w_ratio_rank,
    f.vol_1m_rank, f.vol_3m_rank, f.beta_1y_rank, f.idio_vol_rank,
    f.adv_20d_rank, f.vol_surge_rank,
    f.score_mom, f.score_lowvol, f.score_liq, f.score_composite
from read_parquet('../../data/marts/fct_stock_features.parquet') f
join read_parquet('../../data/marts/dim_universe_history.parquet') u on f.sk_dim_universe_history = u.sk_id
