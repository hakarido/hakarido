#!/usr/bin/env python3
"""lint_all.py — 週4用。静的解析の検出密度（100行あたり）を1行の CSV にする。

使い方:
  python bench/lint_all.py --label AI    corpus_ai    --out results/lint.csv
  python bench/lint_all.py --label human corpus_human --out results/lint.csv

使う道具（.venv に入れておく）: ruff, mypy, bandit, radon。入っていない道具の列は NA になる。
数える指標:
  - 行数（.py の物理行）
  - ruff --select ALL の検出総数と /100行、上位ルール3（ruff.toml を置けばそれが使われる）
  - mypy --strict のエラー数と /100行
  - bandit の High / Medium / Low
  - radon の平均複雑度と最大複雑度（関数名つき）
  - except 節の中身が pass / ... だけの数、裸の except の数（ast で数える）
  - `type: ignore` の数
  - 関数の数と、関数あたりの平均行数
人間側が悪かった指標も同じ列に出る（一方的な比較にしないため、列を選ばない）。
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

RULE_CODE_RE = re.compile(r"^[A-Z]{1,4}\d{3,4}$")
FIELDS = [
    "label", "files", "lines",
    "ruff_total", "ruff_per100", "ruff_top3",
    "mypy_errors", "mypy_per100",
    "bandit_high", "bandit_medium", "bandit_low",
    "radon_avg_cc", "radon_max_cc", "radon_max_func",
    "except_pass", "bare_except", "type_ignore",
    "functions", "avg_lines_per_function",
]


def py_files(root: Path) -> list[Path]:
    skip = {".venv", "venv", "mutants", "__pycache__", ".git", "node_modules"}
    return sorted(p for p in root.rglob("*.py") if not (set(p.parts) & skip))


def run(cmd: list[str]) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return None


def per100(n: int | str, lines: int) -> str:
    if isinstance(n, str) or not lines:
        return "NA"
    return f"{n / lines * 100:.2f}"


def ruff_stats(root: Path) -> tuple[int | str, str]:
    r = run(["ruff", "check", "--select", "ALL", "--statistics", "--exit-zero", str(root)])
    if r is None:
        return "NA", "NA"
    counts: Counter[str] = Counter()
    for line in r.stdout.splitlines():
        tokens = line.replace("\t", " ").split()
        count = next((int(t) for t in tokens if t.isdigit()), None)
        code = next((t for t in tokens if RULE_CODE_RE.match(t)), None)
        if count is not None and code:
            counts[code] += count
    top3 = "; ".join(f"{c} {n}" for c, n in counts.most_common(3))
    return sum(counts.values()), top3


def mypy_errors(root: Path) -> int | str:
    r = run(["mypy", "--strict", "--no-error-summary", "--no-color-output", "--hide-error-context", str(root)])
    if r is None:
        return "NA"
    return sum(1 for ln in r.stdout.splitlines() if ": error:" in ln)


def bandit_counts(root: Path) -> tuple[int | str, int | str, int | str]:
    r = run(["bandit", "-r", "-q", "-f", "json", str(root)])
    if r is None:
        return "NA", "NA", "NA"
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return "NA", "NA", "NA"
    sev = Counter(item.get("issue_severity", "").upper() for item in data.get("results", []))
    return sev.get("HIGH", 0), sev.get("MEDIUM", 0), sev.get("LOW", 0)


def radon_cc(root: Path) -> tuple[str, str, str]:
    r = run(["radon", "cc", "-j", str(root)])
    if r is None:
        return "NA", "NA", "NA"
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return "NA", "NA", "NA"
    blocks = []
    for file, items in data.items():
        if not isinstance(items, list):
            continue
        for b in items:
            if "complexity" in b:
                blocks.append((b["complexity"], f"{Path(file).name}:{b.get('name', '?')}"))
    if not blocks:
        return "0", "0", ""
    avg = sum(c for c, _ in blocks) / len(blocks)
    mx = max(blocks)
    return f"{avg:.2f}", str(mx[0]), mx[1]


def ast_counts(files: list[Path]) -> dict[str, int | str]:
    except_pass = bare = funcs = func_lines = 0
    type_ignore = 0
    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (SyntaxError, ValueError):
            continue
        type_ignore += sum(1 for ln in src.splitlines() if "type: ignore" in ln)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bare += 1
                body = node.body
                if len(body) == 1 and (isinstance(body[0], ast.Pass) or (
                        isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant)
                        and body[0].value.value is Ellipsis)):
                    except_pass += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs += 1
                if getattr(node, "end_lineno", None):
                    func_lines += node.end_lineno - node.lineno + 1
    return {
        "except_pass": except_pass, "bare_except": bare, "type_ignore": type_ignore,
        "functions": funcs, "avg_lines_per_function": f"{func_lines / funcs:.1f}" if funcs else "0",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("--label", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    root = Path(a.root)
    files = py_files(root)
    lines = sum(sum(1 for _ in f.open(encoding="utf-8", errors="replace")) for f in files)

    ruff_total, ruff_top3 = ruff_stats(root)
    mypy_n = mypy_errors(root)
    b_h, b_m, b_l = bandit_counts(root)
    cc_avg, cc_max, cc_func = radon_cc(root)
    extra = ast_counts(files)

    row = {
        "label": a.label, "files": len(files), "lines": lines,
        "ruff_total": ruff_total, "ruff_per100": per100(ruff_total, lines), "ruff_top3": ruff_top3,
        "mypy_errors": mypy_n, "mypy_per100": per100(mypy_n, lines),
        "bandit_high": b_h, "bandit_medium": b_m, "bandit_low": b_l,
        "radon_avg_cc": cc_avg, "radon_max_cc": cc_max, "radon_max_func": cc_func,
        **extra,
    }

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new = not out.exists()
    with out.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)

    for k in FIELDS:
        print(f"{k}: {row[k]}")
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
