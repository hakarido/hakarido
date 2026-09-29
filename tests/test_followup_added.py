"""追加テスト：week01 の生存ミュータント上位種を狙って追加したもの。

下書き：Claude（生存ミュータント一覧を見て作成）。本人は内容確認のみ。
計画では「人間が5分で書く」だったが、実際の作成者に合わせてこの表記にしている。
狙い：例外メッセージ非照合（22体）、境界・定数（数体）、parse_csv の区切り文字伝播（2体）。
"""
import re

from datetime import date

import pytest

from target import (
    DateRange,
    merge_ranges,
    parse_csv,
    parse_csv_line,
    round_yen,
    split_evenly,
    with_tax,
)


def test_daterange_error_message():
    """逆転した日付範囲のエラーメッセージが仕様どおりであることを検証する。"""
    with pytest.raises(ValueError, match=re.escape("end must not be before start")):
        DateRange(date(2026, 1, 2), date(2026, 1, 1))


def test_round_yen_unknown_mode_message():
    """未知の丸めモードのエラーメッセージにモード名が含まれることを検証する。"""
    with pytest.raises(ValueError, match=re.escape("unknown rounding mode: 'ceiling'")):
        round_yen(100, mode="ceiling")


def test_with_tax_error_messages():
    """with_tax の負数エラーのメッセージが仕様どおりであることを検証する。"""
    with pytest.raises(ValueError, match=re.escape("net must be >= 0")):
        with_tax(-1)
    with pytest.raises(ValueError, match=re.escape("rate_percent must be >= 0")):
        with_tax(100, rate_percent=-5)


def test_split_evenly_error_messages():
    """split_evenly の引数エラーのメッセージが仕様どおりであることを検証する。"""
    with pytest.raises(ValueError, match=re.escape("parts must be >= 1")):
        split_evenly(100, 0)
    with pytest.raises(ValueError, match=re.escape("total must be >= 0")):
        split_evenly(-100, 2)


def test_parse_csv_line_error_messages():
    """parse_csv_line の2種のエラーメッセージが仕様どおりであることを検証する。"""
    with pytest.raises(ValueError, match=re.escape("delimiter must be a single character")):
        parse_csv_line("a,b", delimiter=",,")
    with pytest.raises(ValueError, match=re.escape("unterminated quoted field")):
        parse_csv_line('a,"bc')


def test_with_tax_zero_boundaries():
    """税抜0円と税率0%が正常入力として受理されることを検証する。"""
    assert with_tax(0) == 0
    assert with_tax(100, rate_percent=0) == 100


def test_split_evenly_single_part():
    """parts=1 で全額が1人に割り当てられることを検証する。"""
    assert split_evenly(100, 1) == [100]


def test_merge_ranges_exact_one_day_gap_stays_separate():
    """ちょうど1日空いた2範囲（結合してはいけない境界）が別々のままであることを検証する。"""
    ranges = [
        DateRange(date(2026, 1, 1), date(2026, 1, 3)),
        DateRange(date(2026, 1, 5), date(2026, 1, 7)),
    ]
    assert merge_ranges(ranges) == ranges


def test_parse_csv_passes_delimiter_through():
    """parse_csv が見出し行と本体行の両方に区切り文字を渡していることを検証する。"""
    assert parse_csv("name;price\napple;100\n", delimiter=";") == [
        {"name": "apple", "price": "100"}
    ]
