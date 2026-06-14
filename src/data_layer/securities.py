"""종목 마스터(security reference). symbol(코드) → name(종목명)·market 매핑.

가격·유니버스는 symbol(KRX 6자리 코드)만 들고 있어 "어느 종목인지" 알 수 없다. 이 참조를
조인해 종목명을 붙인다. 출처는 FDR StockListing(종목명·시장 제공).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from data_layer.universe import DEFAULT_DATA_DIR

# 저장 스키마. symbol = KRX 6자리 코드(0패딩 str), name = 종목명, market = 시장.
SECURITY_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.String(),
    "name": pl.String(),
    "market": pl.String(),
}


def securities_path(name: str, data_dir: Path | None = None) -> Path:
    """`name`(시장) 종목 마스터의 parquet 경로."""
    return (data_dir or DEFAULT_DATA_DIR) / "reference" / "securities" / f"{name}.parquet"
