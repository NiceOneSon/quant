"""FinanceDataReader(FDR) 기반 일별 OHLCV 소스 (수정주가).

pykrx 와 독립적인 대안/폴백. KRX 종목은 6자리 코드(예: '005930')를 그대로 쓴다.

⚠️ FDR 은 KRX 종목에 **수정주가만** 제공한다(원본가 옵션 없음 — 시그니처·data_source 모두
확인됨). 따라서 close_raw 는 항상 null 이다. 원본가/수정계수가 필요하면 다른 경로가 필요하다.
pykrx 의 수정주가와 마찬가지로 "오늘 기준" 역산값이라 장기 백테스트에선 약한 룩어헤드가 있다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

import polars as pl

from data_layer.universe import Membership

# (ticker, start, end) -> date/open/high/low/close/volume 프레임. 테스트에서 주입해 모킹.
FdrReadFn = Callable[[str, date, date], pl.DataFrame]
# market -> 종목코드 리스트. 테스트에서 주입해 모킹.
ListingFn = Callable[[str], list[str]]

# 유니버스 이름 -> FDR StockListing 시장. FDR 은 KOSPI200 같은 지수는 미지원.
# Yahoo Finance 원자재 선물 티커 (FdrSeriesSource 에 그대로 전달)
YAHOO_WTI = "CL=F"     # WTI 원유 근월물 ($/bbl) — 당일 종가, EIA 스팟 대비 수 센트 차이
YAHOO_BRENT = "BZ=F"   # Brent 원유 근월물 ($/bbl)

_DEFAULT_MARKETS = {"kospi": "KOSPI", "kosdaq": "KOSDAQ", "krx": "KRX"}

_OHLCV_COLS = ["date", "open", "high", "low", "close", "volume"]
# FDR 한글 아님 — 영문 컬럼. reset_index 후 'Date' 컬럼이 생긴다.
_FDR_RENAME = {
    "Date": "date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}


def _fdr_ohlcv(ticker: str, start: date, end: date) -> pl.DataFrame:
    """FDR 로 수정주가 OHLCV 를 조회해 표준 컬럼 polars 프레임으로 반환한다 (네트워크 격리)."""
    import FinanceDataReader as fdr  # 지연 import: 선택 의존성('data' extra)

    pdf = fdr.DataReader(ticker, start.isoformat(), end.isoformat())
    if pdf.empty:
        return pl.DataFrame(schema={c: pl.Float64() for c in _OHLCV_COLS} | {"date": pl.Date()})
    frame = pl.from_pandas(pdf.reset_index())
    return frame.rename(_FDR_RENAME).with_columns(pl.col("date").cast(pl.Date)).select(_OHLCV_COLS)


@dataclass
class FdrPriceSource:
    """FDR 수정주가 OHLCV 소스. FDR 은 원본가를 주지 않으므로 close_raw 는 null.

    Attributes:
        read_fn: OHLCV 조회 함수. None 이면 FDR 실호출. 테스트에서 주입해 모킹.
    """

    read_fn: FdrReadFn | None = None

    def fetch(self, ticker: str, start: date, end: date) -> pl.DataFrame:
        fn = self.read_fn or _fdr_ohlcv
        df = fn(ticker, start, end)
        # FDR 은 수정주가 전용 → 원본 종가 없음.
        return df.with_columns(pl.lit(None, dtype=pl.Float64).alias("close_raw"))


def _fdr_listing(market: str) -> list[str]:
    """FDR StockListing 으로 `market` 의 현재 상장 종목코드를 반환한다 (네트워크 격리)."""
    import FinanceDataReader as fdr  # 지연 import: 선택 의존성('data' extra)

    df = fdr.StockListing(market)
    return [str(code) for code in df["Code"].tolist()]


# market -> 종목 마스터 프레임(symbol, name, market). 테스트에서 주입해 모킹.
SecurityListingFn = Callable[[str], pl.DataFrame]


def _fdr_securities(market: str) -> pl.DataFrame:
    """FDR StockListing 으로 `market` 의 종목 마스터(symbol, name, market)를 반환한다.

    문자열 컬럼이라 pl.from_pandas(pyarrow 필요) 대신 리스트로 직접 구성한다.
    """
    import FinanceDataReader as fdr  # 지연 import: 선택 의존성('data' extra)

    pdf = fdr.StockListing(market)
    return pl.DataFrame(
        {
            "symbol": [str(c) for c in pdf["Code"].tolist()],
            "name": [str(n) for n in pdf["Name"].tolist()],
            "market": [str(m) for m in pdf["Market"].tolist()],
        }
    )


@dataclass
class FdrSecuritySource:
    """FDR StockListing 기반 종목 마스터 소스 (symbol → name, market).

    Attributes:
        listing_fn: 조회 함수. None 이면 FDR 실호출. 테스트에서 주입해 모킹.
        markets: 이름 -> FDR 시장 매핑.
    """

    listing_fn: SecurityListingFn | None = None
    markets: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_MARKETS))

    def fetch(self, name: str) -> pl.DataFrame:
        market = self.markets.get(name)
        if market is None:
            raise ValueError(f"FDR 종목 마스터 미지원: {name!r}. 지원: {sorted(self.markets)}")
        fn = self.listing_fn or _fdr_securities
        return fn(market)


SeriesReadFn = Callable[[str, date, date], pl.DataFrame]


def _fdr_series(series: str, start: date, end: date) -> pl.DataFrame:
    """FDR 로 FX·지수·ETF 시계열을 조회해 date/value 프레임으로 반환한다 (네트워크 격리).

    예) 'USD/KRW', 'KS11', 'Gold', 'SLV'
    OHLCV 응답(Gold, ETF 등)은 Close 컬럼 우선, 없으면 첫 번째 컬럼.
    pl.from_pandas(pyarrow 필요) 대신 리스트 직접 구성 — FX nullable Int64 대응.
    """
    import FinanceDataReader as fdr  # 지연 import: 선택 의존성('data' extra)

    pdf = fdr.DataReader(series, start.isoformat(), end.isoformat())
    if pdf is None or pdf.empty:
        return pl.DataFrame(schema={"date": pl.Date(), "value": pl.Float64()})
    # 인덱스(날짜) → date 리스트; 값은 Close 우선, 없으면 첫 번째 컬럼.
    dates = [d.date() if hasattr(d, "date") else d for d in pdf.index.tolist()]
    value_col = pdf["Close"] if "Close" in pdf.columns else pdf.iloc[:, 0]
    values = [float(v) if v is not None else float("nan") for v in value_col.tolist()]
    return pl.DataFrame({"date": dates, "value": values}).with_columns(
        pl.col("date").cast(pl.Date),
        pl.col("value").cast(pl.Float64),
    )


@dataclass
class FdrSeriesSource:
    """FDR 기반 FX·지수 시계열 소스 (date, value).

    series 예: 'USD/KRW', 'USD/JPY', 'KS11'(KOSPI), 'KS200'(KOSPI200), 'KQ11'(KOSDAQ).

    Attributes:
        series: FDR 에 전달할 시리즈 코드.
        read_fn: 조회 함수. None 이면 FDR 실호출. 테스트에서 주입해 모킹.
    """

    series: str
    read_fn: SeriesReadFn | None = None

    def fetch(self, start: date, end: date) -> pl.DataFrame:
        fn = self.read_fn or _fdr_series
        return fn(self.series, start, end)


@dataclass
class FdrUniverseSource:
    """FDR StockListing 기반 유니버스 소스 — 깨진 PykrxUniverseSource 대체.

    현재 상장 종목을 `asof` 기준 스냅샷으로 반환한다(added=asof, removed=None).

    ⚠️ **생존편향 주의**: StockListing 은 *현재 상장* 종목만 준다(상장폐지 종목 없음).
    또한 added=asof 이므로 `asof` 이전 날짜의 members_asof 는 비어 있다. 따라서 단일 스냅샷은
    "현재/최근 유니버스"용이다. 과거 PIT 이력이 필요하면 시점마다 스냅샷을 ingest 해 누적한
    뒤 snapshots_to_memberships 로 구간을 복원해야 한다(단일 호출로는 과거 백필 불가).

    FDR 은 KOSPI200 같은 지수 구성종목은 미지원 — 시장 단위(kospi/kosdaq/krx)만 가능.

    Attributes:
        asof: 스냅샷 기준일 (added 로 기록).
        listing_fn: 상장목록 조회 함수. None 이면 FDR 실호출. 테스트에서 주입해 모킹.
        markets: 유니버스 이름 -> FDR 시장 매핑.
    """

    asof: date
    listing_fn: ListingFn | None = None
    markets: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_MARKETS))

    def fetch(self, name: str) -> list[Membership]:
        market = self.markets.get(name)
        if market is None:
            raise ValueError(
                f"FDR 유니버스 미지원: {name!r}. 지원: {sorted(self.markets)} "
                "(KOSPI200 같은 지수는 FDR 로 불가)"
            )
        fn = self.listing_fn or _fdr_listing
        codes = fn(market)
        return [
            Membership(symbol=code, added=self.asof, removed=None) for code in sorted(set(codes))
        ]
