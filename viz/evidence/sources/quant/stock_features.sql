-- fct_stock_features: 종목 단면 팩터. name 기준 노출 (symbol 코드 제외).
select
    date, name, universe,
    mom_1m, mom_6m, mom_12_1m, rev_1w, hi52w_ratio,
    vol_1m, vol_3m, beta_1y, idio_vol_1m,
    adv_20d, vol_surge,
    mom_12_1m_rank, mom_6m_rank, mom_1m_rank, rev_1w_rank, hi52w_ratio_rank,
    vol_1m_rank, vol_3m_rank, beta_1y_rank, idio_vol_rank,
    adv_20d_rank, vol_surge_rank,
    score_mom, score_lowvol, score_liq, score_composite
from read_parquet('../../data/marts/fct_stock_features.parquet')
