"""target.py — 週1「カバレッジ100%のAIテストは、ミュータントの何%を見逃すか」の対象モジュール。

依存なしの純粋関数だけで構成する。3つの小さな領域：
  1. 日付範囲（両端を含む）の重なり判定・重なり日数・結合
  2. 金額（円）の端数処理・税込計算・等分
  3. 1行CSVの分解（ダブルクオート囲み・"" エスケープ対応。改行を含む項目は非対応）

MIT License. Copyright (c) 2026 hakarido
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Iterable

# ---------------------------------------------------------------------------
# 1. 日付範囲
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DateRange:
    """両端を含む日付範囲。end が start より前なら ValueError。"""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("end must not be before start")

    @property
    def days(self) -> int:
        """範囲に含まれる日数（start と end が同じ日なら 1）。"""
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        """day が範囲内（両端を含む）なら True。"""
        return self.start <= day <= self.end


def overlaps(a: DateRange, b: DateRange) -> bool:
    """1日でも共有していれば True。端の日が同じ場合も重なりとみなす。"""
    return a.start <= b.end and b.start <= a.end


def overlap_days(a: DateRange, b: DateRange) -> int:
    """共有している日数。重ならなければ 0。"""
    if not overlaps(a, b):
        return 0
    start = max(a.start, b.start)
    end = min(a.end, b.end)
    return (end - start).days + 1


def merge_ranges(ranges: Iterable[DateRange]) -> list[DateRange]:
    """重なる範囲と隣接する範囲（翌日から始まる）を結合し、開始日順に返す。"""
    ordered = sorted(ranges, key=lambda r: (r.start, r.end))
    merged: list[DateRange] = []
    for current in ordered:
        if not merged:
            merged.append(current)
            continue
        last = merged[-1]
        if current.start <= last.end + timedelta(days=1):
            if current.end > last.end:
                merged[-1] = DateRange(last.start, current.end)
        else:
            merged.append(current)
    return merged


# ---------------------------------------------------------------------------
# 2. 金額（円）
# ---------------------------------------------------------------------------

_ROUNDING = {
    "half_up": ROUND_HALF_UP,
    "half_even": ROUND_HALF_EVEN,
    "down": ROUND_DOWN,
}


def round_yen(amount: Decimal | int | float | str, mode: str = "half_up") -> int:
    """1円単位に丸める。mode は half_up（四捨五入）／half_even（銀行丸め）／down（切り捨て）。

    float は文字列経由で Decimal にするので、0.1 + 0.2 のような二進誤差を持ち込まない。
    """
    if mode not in _ROUNDING:
        raise ValueError(f"unknown rounding mode: {mode!r}")
    value = Decimal(str(amount))
    return int(value.quantize(Decimal("1"), rounding=_ROUNDING[mode]))


def with_tax(net: int, rate_percent: int = 10, mode: str = "down") -> int:
    """税抜額（整数円）から税込額を返す。既定は 10%・切り捨て。負の金額・負の税率は不可。"""
    if net < 0:
        raise ValueError("net must be >= 0")
    if rate_percent < 0:
        raise ValueError("rate_percent must be >= 0")
    gross = Decimal(net) * (Decimal(100) + Decimal(rate_percent)) / Decimal(100)
    return round_yen(gross, mode)


def split_evenly(total: int, parts: int) -> list[int]:
    """total 円を parts 人で分ける。余りは先頭から 1 円ずつ配る。合計は必ず total に一致する。"""
    if parts <= 0:
        raise ValueError("parts must be >= 1")
    if total < 0:
        raise ValueError("total must be >= 0")
    base, remainder = divmod(total, parts)
    return [base + 1 if i < remainder else base for i in range(parts)]


# ---------------------------------------------------------------------------
# 3. CSV
# ---------------------------------------------------------------------------


def parse_csv_line(line: str, delimiter: str = ",") -> list[str]:
    """1行を項目に分ける。

    - ダブルクオートで囲まれた項目の中では区切り文字をそのまま扱う
    - 囲みの中の "" は 1 文字の " にする
    - 閉じられていない囲みは ValueError
    - 改行を含む項目は扱わない（呼び出し側で1行ずつ渡す）
    """
    if len(delimiter) != 1:
        raise ValueError("delimiter must be a single character")
    fields: list[str] = []
    buf: list[str] = []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < len(line) and line[i + 1] == '"':
                    buf.append('"')
                    i += 1
                else:
                    in_quotes = False
            else:
                buf.append(ch)
        elif ch == '"':
            in_quotes = True
        elif ch == delimiter:
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if in_quotes:
        raise ValueError("unterminated quoted field")
    fields.append("".join(buf))
    return fields


def parse_csv(text: str, delimiter: str = ",") -> list[dict[str, str]]:
    """先頭行を見出しとして各行を dict にする。空行は読み飛ばす。項目数が見出しと違う行は ValueError。"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = parse_csv_line(lines[0], delimiter)
    rows: list[dict[str, str]] = []
    for number, line in enumerate(lines[1:], start=2):
        values = parse_csv_line(line, delimiter)
        if len(values) != len(header):
            raise ValueError(f"line {number}: expected {len(header)} fields, got {len(values)}")
        rows.append(dict(zip(header, values)))
    return rows
