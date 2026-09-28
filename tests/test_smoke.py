"""ハーネスの動作確認用。★週1の計測前に削除する（git rm tests/test_smoke.py）。

AI生成テスト以外が残っていると、週1の「AI生成テストのみ」の数字が汚れる。
"""
from datetime import date

from target import DateRange, overlaps, parse_csv_line, round_yen, split_evenly


def test_overlaps_touching_edges():
    a = DateRange(date(2026, 1, 1), date(2026, 1, 10))
    b = DateRange(date(2026, 1, 10), date(2026, 1, 20))
    assert overlaps(a, b)


def test_round_yen_half_up():
    assert round_yen("2.5") == 3


def test_split_evenly_remainder_goes_first():
    assert split_evenly(10, 3) == [4, 3, 3]


def test_parse_csv_line_quotes():
    assert parse_csv_line('a,"b,c","d""e"') == ["a", "b,c", 'd"e']
