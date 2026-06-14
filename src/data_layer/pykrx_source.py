"""pykrx 기반 유니버스 멤버십 소스 (국내 지수: KOSPI200 등).

pykrx 는 "특정 날짜의 지수 구성종목 스냅샷"만 제공한다. point-in-time 멤버십 구간
(편입일/편출일)을 얻으려면 기간을 일정 주기로 샘플링한 스냅샷들을 차집합으로 비교해
구간을 복원해야 한다. 이 복원 로직(snapshots_to_memberships)은 순수 함수라 네트워크 없이
테스트한다. 실제 pykrx 호출은 _pykrx_constituents 한 곳에만 격리한다(테스트에서는 주입으로 모킹).

주의:
- pykrx 데이터는 2014-05-02 이후만 조회 가능.
- 샘플링 기반이라 added/removed 는 "관측 시작/종료" 시점이다. start 를 백테스트 기간보다
  충분히 앞에 두어야 첫 편입 시점이 잘리지 않는다.
- 휴일·빈 응답 스냅샷은 건너뛴다(전 종목 편출로 오인 방지). alternative=True 로 직전
  영업일을 쓰지만 방어적으로 한 번 더 거른다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl

from common.logging import get_logger
from data_layer.universe import Membership, snapshots_to_memberships

log = get_logger(__name__)

# (ticker, 조회일) -> 그날의 구성종목 심볼 집합. 테스트에서 이 시그니처로 주입해 모킹한다.
ConstituentsFn = Callable[[str, date], set[str]]
# (ticker, start, end, adjusted) -> 일별 OHLCV 프레임. 테스트에서 주입해 모킹한다.
OhlcvFn = Callable[[str, date, date, bool], pl.DataFrame]

# pykrx 한글 컬럼 -> 표준 영문 컬럼.
_OHLCV_RENAME = {
    "날짜": "date",
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "거래량": "volume",
}

# 지수명 -> pykrx 인덱스 티커. 필요 시 확장.
_DEFAULT_INDEX_TICKERS = {"kospi200": "1028"}


def sample_dates(start: date, end: date, step_days: int) -> list[date]:
    """[start, end] 를 step_days 간격으로 샘플링한다. end 는 항상 포함한다 (순수)."""
    if step_days <= 0:
        raise ValueError("step_days 는 양수여야 합니다.")
    dates: list[date] = []
    cur = start
    while cur < end:
        dates.append(cur)
        cur += timedelta(days=step_days)
    dates.append(end)
    return dates


def _pykrx_constituents(ticker: str, on: date) -> set[str]:
    """pykrx 로 `on` 시점 지수 구성종목을 조회한다 (네트워크 호출 — 여기만 격리)."""
    from pykrx import stock  # 지연 import: 선택 의존성('data' extra)

    codes = stock.get_index_portfolio_deposit_file(ticker, on.strftime("%Y%m%d"), alternative=True)
    return set(codes)


@dataclass
class PykrxUniverseSource:
    """pykrx 지수 구성종목을 샘플링해 point-in-time 멤버십으로 복원하는 소스.

    ⚠️ **현재 동작 안 함**: pykrx 지수 endpoint(`get_index_portfolio_deposit_file` 등)가
    KRX 회귀로 모든 날짜에서 빈 결과를 낸다(pandas 2.x·3.x 무관, 실호출 확인). 유니버스는
    `fdr_source.FdrUniverseSource` 를 쓴다. KRX 가 endpoint 를 복구하면 이 소스도 되살아난다.
    아래 snapshots_to_memberships/sample_dates 순수 로직은 그때(또는 FDR 스냅샷 누적 시) 재사용.

    Attributes:
        start, end: 멤버십을 복원할 기간.
        sample_days: 스냅샷 샘플링 주기(일). 지수 정기변경(보통 반기)보다 촘촘하게.
        index_tickers: 지수명 -> pykrx 티커 매핑.
        constituents_fn: 구성종목 조회 함수. None 이면 pykrx 실호출. 테스트에서 주입해 모킹.
    """

    start: date
    end: date
    sample_days: int = 30
    index_tickers: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_INDEX_TICKERS))
    constituents_fn: ConstituentsFn | None = None

    def fetch(self, name: str) -> list[Membership]:
        ticker = self.index_tickers.get(name)
        if ticker is None:
            raise ValueError(
                f"알 수 없는 유니버스: {name!r}. 등록된 지수: {sorted(self.index_tickers)}"
            )
        fetch_fn = self.constituents_fn or _pykrx_constituents
        snapshots: list[tuple[date, set[str]]] = []
        for on in sample_dates(self.start, self.end, self.sample_days):
            members = fetch_fn(ticker, on)
            if members:  # 휴일/빈 응답은 건너뛴다 (전 종목 편출로 오인 방지)
                snapshots.append((on, members))
        return snapshots_to_memberships(snapshots)


def _pykrx_ohlcv(ticker: str, start: date, end: date, adjusted: bool) -> pl.DataFrame:
    """pykrx 로 일별 OHLCV 를 조회해 표준 컬럼 polars 프레임으로 반환한다 (네트워크 격리)."""
    from pykrx import stock  # 지연 import: 선택 의존성('data' extra)

    pdf = stock.get_market_ohlcv_by_date(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker, adjusted=adjusted
    )
    if pdf.empty:
        return pl.DataFrame(
            schema={c: pl.Float64() for c in _OHLCV_RENAME.values()} | {"date": pl.Date()}
        )
    frame = pl.from_pandas(pdf.reset_index())
    return (
        frame.rename(_OHLCV_RENAME)
        .with_columns(pl.col("date").cast(pl.Date))
        .select(["date", "open", "high", "low", "close", "volume"])
    )


@dataclass
class PykrxPriceSource:
    """pykrx 일별 OHLCV 소스. 수정주가를 기본으로, 원본 종가는 best-effort 로 함께 가져온다.

    수정주가(adjusted=True)는 백테스트가 실제로 쓰는 값이라 항상 채운다. 원본 종가
    (close_raw, 수정계수 복원용)는 pykrx 의 adjusted=False 경로가 버전/환경에 따라 비어 올 수
    있어(예: 1.0.51) best-effort 다 — 비면 경고만 남기고 null 로 둔다.

    주의: pykrx 의 수정주가는 "오늘 기준"으로 역산된 값이다(장기 백테스트에서는 약한 룩어헤드).
    엄밀한 PIT 가 필요하면 시점별 수정계수를 별도 확보해야 한다.

    Attributes:
        ohlcv_fn: OHLCV 조회 함수. None 이면 pykrx 실호출. 테스트에서 주입해 모킹.
    """

    ohlcv_fn: OhlcvFn | None = None

    def _with_null_raw(self, adj: pl.DataFrame) -> pl.DataFrame:
        return adj.with_columns(pl.lit(None, dtype=pl.Float64).alias("close_raw"))

    def fetch(self, ticker: str, start: date, end: date) -> pl.DataFrame:
        fn = self.ohlcv_fn or _pykrx_ohlcv
        adj = fn(ticker, start, end, True)  # 수정주가 OHLCV (항상)
        if adj.height == 0:
            return self._with_null_raw(adj)
        raw = fn(ticker, start, end, False)  # 원본 종가 (best-effort)
        if raw.height == 0:
            log.warning("unadjusted prices unavailable | ticker=%s → close_raw=null", ticker)
            return self._with_null_raw(adj)
        raw_close = raw.select(["date", pl.col("close").alias("close_raw")])
        return adj.join(raw_close, on="date", how="left")
