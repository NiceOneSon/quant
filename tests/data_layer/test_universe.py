from datetime import date

from data_layer.universe import Membership, members_asof


def _sample() -> list[Membership]:
    return [
        Membership("AAA", added=date(2010, 1, 1)),  # 계속 편입
        # BBB 는 2018 년에 상장폐지/편출됨
        Membership("BBB", added=date(2010, 1, 1), removed=date(2018, 6, 1)),
        # CCC 는 2020 년에 신규 편입
        Membership("CCC", added=date(2020, 1, 1)),
    ]


def test_survivorship_delisted_included_at_its_time() -> None:
    # 편출 전 시점에는 편출 종목도 유니버스에 있어야 한다 (생존편향 방지)
    assert members_asof(_sample(), "2017-01-01") == {"AAA", "BBB"}


def test_delisted_excluded_after_removal() -> None:
    # 편출 이후 시점에는 빠진다
    assert members_asof(_sample(), "2019-01-01") == {"AAA"}


def test_not_yet_added_excluded() -> None:
    # 편입 전 종목은 포함되지 않는다 (룩어헤드 방지)
    assert members_asof(_sample(), "2021-01-01") == {"AAA", "CCC"}
