#!/usr/bin/env python3
"""classify_survivors.py — 生存ミュータントを規則で一次分類し、抜き取り検証欄つきの CSV にする。

使い方:
  python scripts/classify_survivors.py --results results/mutmut_results.txt --out results/survivors_week01.csv [--limit 300]
  python scripts/classify_survivors.py --ids-file ids.txt --out ...   # ID を拾えないときは1行1件で渡す

手順:
  1. `mutmut results` の出力から生存（survived）ミュータントの ID を拾う
  2. 各 ID について `mutmut show <ID>` の差分を取る
  3. 差分の変わった部分から種別を付ける（規則ベースの一次分類。LLM は使わない）
  4. CSV に書く。列: mutant_id, auto_category, removed, added, human_checked, human_category, memo
     → 本人が10件を抜き取って human_* 列を埋め、記事でこの手順を開示する
  5. 種別の上位3を標準出力に出す（表の「生存上位種別」列に転記）

★ `mutmut results` の表示形式はバージョンで違う。ID が1件も拾えないときは --ids-file を使う。
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ID_RE = re.compile(r"([A-Za-z_][\w\.]*?__mutmut_\d+)")
STATUS_WORDS = ("survived", "killed", "timeout", "suspicious", "skipped", "no tests", "untested")
CMP_RE = re.compile(r"(<=|>=|==|!=|<|>)")
LOGIC_RE = re.compile(r"\b(and|or|not|True|False|is|in)\b")
ARITH_RE = re.compile(r"(\*\*|//|[-+*/%])")


def survived_ids(text: str) -> list[str]:
    ids: list[str] = []
    section: str | None = None
    for line in text.splitlines():
        low = line.lower()
        has_id = ID_RE.search(line)
        header = next((w for w in STATUS_WORDS if w in low), None) if not has_id else None
        if header:
            section = header
            continue
        if not has_id:
            continue
        if any(w in low for w in STATUS_WORDS):  # 形式B: 「ID: survived」のように1行にまとまる
            if "survived" in low:
                ids.append(has_id.group(1))
            continue
        if section == "survived":  # 形式A: 見出しの下に ID が並ぶ
            ids.append(has_id.group(1))
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def show_diff(mutant_id: str) -> str:
    try:
        r = subprocess.run(["mutmut", "show", mutant_id], capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    return r.stdout or r.stderr


def changed_lines(diff: str) -> tuple[str, str]:
    removed = next((ln[1:].strip() for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")), "")
    added = next((ln[1:].strip() for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")), "")
    return removed, added


def core(a: str, b: str) -> tuple[str, str]:
    """共通の前置き・後置きを削り、変わった部分をトークン境界まで広げて返す。

    "<=" → "<" のような1文字差を "=" だけで見ないために、空白で区切られたトークン全体に広げる。
    """
    i = 0
    n = min(len(a), len(b))
    while i < n and a[i] == b[i]:
        i += 1
    j = 0
    while j < n - i and a[len(a) - 1 - j] == b[len(b) - 1 - j]:
        j += 1
    while i > 0 and not a[i - 1].isspace():
        i -= 1
    end_a, end_b = len(a) - j, len(b) - j
    while end_a < len(a) and not a[end_a].isspace():
        end_a += 1
    while end_b < len(b) and not b[end_b].isspace():
        end_b += 1
    return a[i:end_a], b[i:end_b]


def classify(removed: str, added: str) -> str:
    if not removed and not added:
        return "不明（差分なし）"
    r, a = core(removed, added)
    both = r + " " + a
    if re.search(r"\b(raise|except)\b", removed + added):
        return "例外"
    if removed.lstrip().startswith("return") and "None" in added and "None" not in removed:
        return "戻り値"
    if CMP_RE.search(r) or CMP_RE.search(a):
        return "境界（比較演算子）"
    if LOGIC_RE.search(both):
        return "論理（and/or/not/真偽）"
    if ARITH_RE.search(r) or ARITH_RE.search(a):
        return "算術演算子"
    if re.search(r"\d", both):
        return "定数（数値）"
    if "XX" in a or "'" in both or '"' in both:
        return "定数（文字列）"
    if re.search(r"\b(break|continue|pass)\b", both):
        return "制御（break/continue/pass）"
    return "その他"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", help="mutmut results の出力ファイル")
    p.add_argument("--ids-file", help="ID の一覧（1行1件）。--results で拾えないとき用")
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=300, help="mutmut show を呼ぶ上限（時間の保護）")
    a = p.parse_args()

    ids: list[str] = []
    if a.ids_file:
        ids = [ln.strip() for ln in Path(a.ids_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    elif a.results and Path(a.results).exists():
        ids = survived_ids(Path(a.results).read_text(encoding="utf-8", errors="replace"))
    if not ids:
        print("生存ミュータントの ID を拾えませんでした。`mutmut results` の表示を確認し、--ids-file で渡してください。", file=sys.stderr)
        return 1
    if len(ids) > a.limit:
        print(f"注意: {len(ids)} 件のうち先頭 {a.limit} 件だけ分類します（--limit で変更）", file=sys.stderr)
        ids = ids[: a.limit]

    rows = []
    counter: Counter[str] = Counter()
    for mid in ids:
        diff = show_diff(mid)
        removed, added = changed_lines(diff)
        cat = classify(removed, added)
        counter[cat] += 1
        rows.append({"mutant_id": mid, "auto_category": cat, "removed": removed, "added": added,
                     "human_checked": "", "human_category": "", "memo": ""})

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"survived: {len(rows)} 件 → {out}")
    print("上位種別（表の『生存上位種別』に転記。10件を抜き取って human_* 列で検証する）:")
    for cat, n in counter.most_common(3):
        print(f"  {cat}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
