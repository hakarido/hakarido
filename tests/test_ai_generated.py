"""AI生成テスト：src/target.py の行カバレッジ 100% を目標にした pytest テスト。"""
from datetime import date
from decimal import Decimal

import pytest

from target import (
    DateRange,
    merge_ranges,
    overlap_days,
    overlaps,
    parse_csv,
    parse_csv_line,
    round_yen,
    split_evenly,
    with_tax,
)


# ---------------------------------------------------------------------------
# 1. 日付範囲
# ---------------------------------------------------------------------------


def test_daterange_rejects_end_before_start():
    """end が start より前の DateRange は ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        DateRange(date(2026, 1, 2), date(2026, 1, 1))


def test_daterange_days_single_day():
    """start と end が同じ日のとき days が 1 になることを検証する。"""
    assert DateRange(date(2026, 3, 1), date(2026, 3, 1)).days == 1


def test_daterange_days_multiple_days():
    """複数日にまたがる範囲の days が両端を含んで数えられることを検証する。"""
    assert DateRange(date(2026, 3, 1), date(2026, 3, 10)).days == 10


def test_daterange_contains_boundaries_and_outside():
    """contains が両端で True、範囲外で False を返すことを検証する。"""
    r = DateRange(date(2026, 5, 10), date(2026, 5, 20))
    assert r.contains(date(2026, 5, 10)) is True
    assert r.contains(date(2026, 5, 20)) is True
    assert r.contains(date(2026, 5, 15)) is True
    assert r.contains(date(2026, 5, 9)) is False
    assert r.contains(date(2026, 5, 21)) is False


def test_overlaps_true_when_sharing_edge_day():
    """端の日が同じだけの2範囲でも overlaps が True になることを検証する。"""
    a = DateRange(date(2026, 1, 1), date(2026, 1, 5))
    b = DateRange(date(2026, 1, 5), date(2026, 1, 9))
    assert overlaps(a, b) is True
    assert overlaps(b, a) is True


def test_overlaps_false_when_disjoint():
    """1日も共有しない2範囲で overlaps が False になることを検証する。"""
    a = DateRange(date(2026, 1, 1), date(2026, 1, 5))
    b = DateRange(date(2026, 1, 6), date(2026, 1, 9))
    assert overlaps(a, b) is False


def test_overlap_days_zero_when_disjoint():
    """重ならない2範囲の overlap_days が 0 になることを検証する。"""
    a = DateRange(date(2026, 2, 1), date(2026, 2, 3))
    b = DateRange(date(2026, 2, 10), date(2026, 2, 12))
    assert overlap_days(a, b) == 0


def test_overlap_days_counts_shared_days_inclusive():
    """部分的に重なる2範囲の共有日数が両端を含んで数えられることを検証する。"""
    a = DateRange(date(2026, 2, 1), date(2026, 2, 10))
    b = DateRange(date(2026, 2, 8), date(2026, 2, 20))
    assert overlap_days(a, b) == 3


def test_merge_ranges_empty_input():
    """空の iterable を merge_ranges に渡すと空リストが返ることを検証する。"""
    assert merge_ranges([]) == []


def test_merge_ranges_merges_overlapping_and_adjacent():
    """重なる範囲と翌日から始まる隣接範囲が1つに結合されることを検証する。"""
    ranges = [
        DateRange(date(2026, 1, 1), date(2026, 1, 5)),
        DateRange(date(2026, 1, 4), date(2026, 1, 8)),
        DateRange(date(2026, 1, 9), date(2026, 1, 12)),
    ]
    assert merge_ranges(ranges) == [DateRange(date(2026, 1, 1), date(2026, 1, 12))]


def test_merge_ranges_keeps_gapped_ranges_separate():
    """1日以上空いた範囲は結合されず、開始日順に並ぶことを検証する。"""
    ranges = [
        DateRange(date(2026, 1, 10), date(2026, 1, 12)),
        DateRange(date(2026, 1, 1), date(2026, 1, 3)),
    ]
    assert merge_ranges(ranges) == [
        DateRange(date(2026, 1, 1), date(2026, 1, 3)),
        DateRange(date(2026, 1, 10), date(2026, 1, 12)),
    ]


def test_merge_ranges_contained_range_does_not_extend_end():
    """既存範囲に完全に含まれる範囲を足しても end が伸びないことを検証する。"""
    ranges = [
        DateRange(date(2026, 1, 1), date(2026, 1, 10)),
        DateRange(date(2026, 1, 3), date(2026, 1, 5)),
    ]
    assert merge_ranges(ranges) == [DateRange(date(2026, 1, 1), date(2026, 1, 10))]


# ---------------------------------------------------------------------------
# 2. 金額（円）
# ---------------------------------------------------------------------------


def test_round_yen_half_up():
    """half_up モードで 0.5 が切り上げられる（四捨五入）ことを検証する。"""
    assert round_yen("10.5") == 11
    assert round_yen("10.4") == 10


def test_round_yen_half_even():
    """half_even モードで 0.5 が偶数側に丸められる（銀行丸め）ことを検証する。"""
    assert round_yen("10.5", mode="half_even") == 10
    assert round_yen("11.5", mode="half_even") == 12


def test_round_yen_down():
    """down モードで小数部が切り捨てられることを検証する。"""
    assert round_yen("10.9", mode="down") == 10


def test_round_yen_accepts_float_without_binary_error():
    """float 入力が文字列経由で変換され、二進誤差を持ち込まないことを検証する。"""
    assert round_yen(0.1 + 0.2, mode="down") == 0
    assert round_yen(100.5) == 101


def test_round_yen_accepts_int_and_decimal():
    """int と Decimal の入力がそのままの値で丸められることを検証する。"""
    assert round_yen(42) == 42
    assert round_yen(Decimal("7.5")) == 8


def test_round_yen_unknown_mode_raises():
    """未知の丸めモードを渡すと ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        round_yen(100, mode="ceiling")


def test_with_tax_default_10_percent_down():
    """既定の 10%・切り捨てで税込額が計算されることを検証する。"""
    assert with_tax(999) == 1098


def test_with_tax_custom_rate_and_mode():
    """税率と丸めモードを指定した税込計算が正しいことを検証する。"""
    assert with_tax(999, rate_percent=8, mode="half_up") == 1079


def test_with_tax_negative_net_raises():
    """負の税抜額を渡すと ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        with_tax(-1)


def test_with_tax_negative_rate_raises():
    """負の税率を渡すと ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        with_tax(100, rate_percent=-5)


def test_split_evenly_distributes_remainder_from_front():
    """余りが先頭から 1 円ずつ配られ、合計が total に一致することを検証する。"""
    result = split_evenly(1000, 3)
    assert result == [334, 333, 333]
    assert sum(result) == 1000


def test_split_evenly_exact_division():
    """割り切れる場合に全員が同額になることを検証する。"""
    assert split_evenly(900, 3) == [300, 300, 300]


def test_split_evenly_zero_total():
    """total が 0 のとき全員 0 円になることを検証する。"""
    assert split_evenly(0, 4) == [0, 0, 0, 0]


def test_split_evenly_nonpositive_parts_raises():
    """parts が 0 以下のとき ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        split_evenly(100, 0)


def test_split_evenly_negative_total_raises():
    """負の total を渡すと ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        split_evenly(-100, 2)


# ---------------------------------------------------------------------------
# 3. CSV
# ---------------------------------------------------------------------------


def test_parse_csv_line_simple_fields():
    """クオートのない行が区切り文字で分割されることを検証する。"""
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_parse_csv_line_quoted_field_keeps_delimiter():
    """ダブルクオート内の区切り文字が分割されずそのまま残ることを検証する。"""
    assert parse_csv_line('a,"b,c",d') == ["a", "b,c", "d"]


def test_parse_csv_line_escaped_quote():
    """囲みの中の "" が 1 文字の " になることを検証する。"""
    assert parse_csv_line('"say ""hi""",x') == ['say "hi"', "x"]


def test_parse_csv_line_quote_at_end_of_line():
    """行末で閉じるクオート（次の文字がない場合）が正しく処理されることを検証する。"""
    assert parse_csv_line('a,"b"') == ["a", "b"]


def test_parse_csv_line_unterminated_quote_raises():
    """閉じられていないクオートで ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        parse_csv_line('a,"bc')


def test_parse_csv_line_empty_fields():
    """空文字列や連続する区切り文字が空項目として扱われることを検証する。"""
    assert parse_csv_line("") == [""]
    assert parse_csv_line("a,,b") == ["a", "", "b"]


def test_parse_csv_line_custom_delimiter():
    """区切り文字を変更しても分割とクオート処理が機能することを検証する。"""
    assert parse_csv_line('a;"b;c";d', delimiter=";") == ["a", "b;c", "d"]


def test_parse_csv_line_multichar_delimiter_raises():
    """2文字以上の区切り文字で ValueError になることを検証する。"""
    with pytest.raises(ValueError):
        parse_csv_line("a,b", delimiter=",,")


def test_parse_csv_empty_text_returns_empty_list():
    """空文字列や空行だけのテキストで空リストが返ることを検証する。"""
    assert parse_csv("") == []
    assert parse_csv("\n  \n") == []


def test_parse_csv_maps_rows_to_header():
    """先頭行を見出しとして各行が dict になり、空行が読み飛ばされることを検証する。"""
    text = "name,price\n\napple,100\nbanana,80\n"
    assert parse_csv(text) == [
        {"name": "apple", "price": "100"},
        {"name": "banana", "price": "80"},
    ]


def test_parse_csv_field_count_mismatch_raises():
    """項目数が見出しと違う行で行番号入りの ValueError になることを検証する。"""
    with pytest.raises(ValueError, match="line 2"):
        parse_csv("a,b\n1,2,3\n")
