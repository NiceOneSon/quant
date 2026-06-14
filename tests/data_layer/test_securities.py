from pathlib import Path

import polars as pl
import pytest

from data_layer.fdr_source import FdrSecuritySource
from data_layer.ingest import ingest_securities
from data_layer.securities import SECURITY_SCHEMA, securities_path


def _fake_listing(market: str) -> pl.DataFrame:
    assert market == "KOSPI"
    return pl.DataFrame(
        {
            "symbol": ["005930", "000660"],
            "name": ["삼성전자", "SK하이닉스"],
            "market": ["KOSPI", "KOSPI"],
        }
    )


def test_ingest_securities_maps_symbol_to_name(tmp_path: Path) -> None:
    ingest_securities(FdrSecuritySource(listing_fn=_fake_listing), "kospi", data_dir=tmp_path)
    df = pl.read_parquet(securities_path("kospi", tmp_path))

    assert df.schema == pl.Schema(SECURITY_SCHEMA)
    mapping = dict(zip(df["symbol"].to_list(), df["name"].to_list(), strict=True))
    assert mapping == {"005930": "삼성전자", "000660": "SK하이닉스"}


def test_fdr_security_source_rejects_unknown_market() -> None:
    with pytest.raises(ValueError):
        FdrSecuritySource().fetch("sp500")
