#!/usr/bin/env python3
"""scorecard.py — 「行カバレッジ／ミューテーションスコア／モデル名／日付」を1枚の画像にする（反応の装置）。

使い方（Makefile の `make card` が呼ぶ）:
  python scripts/scorecard.py --model "Claude Code / <model>" --date 2026-10-05 --week 01 \
      --coverage results/coverage.json --mutmut-log results/mutmut_run.log \
      --mutmut-results results/mutmut_results.txt --seconds-file results/mutmut_seconds.txt \
      --append-csv results/week01.csv --out results/scorecard_week01

数字の出所:
  - 行カバレッジ: coverage.json の totals.percent_covered（pytest --cov-report=json）
  - killed / survived / timeout / suspicious: mutmut の実行ログと `mutmut results` の出力を正規表現で拾う。
    拾えなければ --killed --survived --timeout --suspicious で直接渡す。
    ★初回は必ず `mutmut results` の表示と目視で照合すること（mutmut のバージョンで表示形式が違う）。
  - スコア% = killed ÷ (killed + survived) × 100。timeout・suspicious は分母に入れず別掲する（記事にもこの定義を書く）。

出力:
  - <out>.svg  … 標準ライブラリだけで生成（常に出る）
  - <out>.png  … matplotlib がある場合のみ
  - --append-csv があれば 1 行追記（ヘッダは無ければ書く）
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

# mutmut 3.8 の最終行（mutmut/stats.py print_stats）:
#   "{tried}/{total}  🎉 {killed} 🫥 {no_tests}  ⏰ {timeout}  🤔 {suspicious}  🙁 {survived}  🔇 {skipped}  🧙 {caught_by_type_check}"
# `mutmut results` は killed 以外を "    {mutant_name}: {status}" で1行ずつ出す（集計行は無い）。
STATUS_PATTERNS = {
    "killed": [r"🎉\s*(\d+)", r"(?i)\bkilled\b\D{0,8}(\d+)"],
    "survived": [r"🙁\s*(\d+)", r"(?i)\bsurvived\b\D{0,8}(\d+)"],
    "timeout": [r"⏰\s*(\d+)", r"(?i)\btimeout\b\D{0,8}(\d+)"],
    "suspicious": [r"🤔\s*(\d+)", r"(?i)\bsuspicious\b\D{0,8}(\d+)"],
    "no_tests": [r"🫥\s*(\d+)", r"(?i)\bno tests\b\D{0,8}(\d+)"],
    "skipped": [r"🔇\s*(\d+)", r"(?i)\bskipped\b\D{0,8}(\d+)"],
    "type_check": [r"🧙\s*(\d+)"],
}

CSV_FIELDS = [
    "week", "label", "date", "model", "coverage_pct", "mutants_total",
    "killed", "survived", "timeout", "suspicious", "score_pct", "mutmut_seconds", "note",
]


def read_text(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def parse_counts(text: str) -> dict[str, int]:
    """ログ中の最後に出てくる集計行を採用する（進行中の途中経過より最終値が後ろに来る）。"""
    counts: dict[str, int] = {}
    for key, patterns in STATUS_PATTERNS.items():
        for pat in patterns:
            found = re.findall(pat, text)
            if found:
                counts[key] = int(found[-1])
                break
    return counts


def read_coverage(path: str | None) -> float | None:
    if not path or not Path(path).exists():
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return float(data["totals"]["percent_covered"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def fmt_pct(v: float | None) -> str:
    return "—" if v is None else f"{v:.1f}%"


def write_svg(path: Path, d: dict) -> None:
    e = html.escape
    title = f"week {d['week']} · {d['label']}"
    line3 = (f"killed {d['killed']} / survived {d['survived']} / timeout {d['timeout']} / "
             f"suspicious {d['suspicious']}   ({d['seconds_label']})")
    footer = "score = killed ÷ (killed + survived)。timeout・suspicious は分母に含めない。n=1 の事例であり一般化しない。"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="480" viewBox="0 0 900 480">
<rect width="900" height="480" fill="#f6f4ee"/>
<rect x="24" y="24" width="852" height="432" rx="16" fill="#ffffff" stroke="#d8d2c2"/>
<g font-family="Noto Sans CJK JP, Noto Sans JP, Segoe UI, Hiragino Sans, sans-serif">
<text x="60" y="84" font-size="26" fill="#2f2e2a">{e(title)}</text>
<text x="60" y="180" font-size="20" fill="#6b685f">行カバレッジ</text>
<text x="60" y="270" font-size="84" font-weight="700" fill="#1f6f4a">{e(fmt_pct(d['coverage']))}</text>
<text x="470" y="180" font-size="20" fill="#6b685f">ミューテーションスコア</text>
<text x="470" y="270" font-size="84" font-weight="700" fill="#b23a2e">{e(fmt_pct(d['score']))}</text>
<text x="60" y="340" font-size="19" fill="#2f2e2a">{e(line3)}</text>
<text x="60" y="392" font-size="19" fill="#6b685f">{e(d['model'])} · {e(d['date'])}</text>
<text x="60" y="432" font-size="14" fill="#8a867a">{e(footer)}</text>
</g>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def write_png(path: Path, d: dict) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except Exception:
        return False
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "Yu Gothic", "Meiryo"):
        if name in available:
            plt.rcParams["font.family"] = name
            break
    fig = plt.figure(figsize=(9, 4.8), dpi=150)
    fig.patch.set_facecolor("#f6f4ee")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.027, 0.05), 0.946, 0.9, transform=ax.transAxes,
                               facecolor="white", edgecolor="#d8d2c2", linewidth=1, zorder=0))
    ax.text(0.067, 0.83, f"week {d['week']} · {d['label']}", fontsize=15, color="#2f2e2a")
    ax.text(0.067, 0.63, "行カバレッジ", fontsize=11, color="#6b685f")
    ax.text(0.067, 0.42, fmt_pct(d["coverage"]), fontsize=44, fontweight="bold", color="#1f6f4a")
    ax.text(0.52, 0.63, "ミューテーションスコア", fontsize=11, color="#6b685f")
    ax.text(0.52, 0.42, fmt_pct(d["score"]), fontsize=44, fontweight="bold", color="#b23a2e")
    ax.text(0.067, 0.29, f"killed {d['killed']} / survived {d['survived']} / timeout {d['timeout']} / "
                         f"suspicious {d['suspicious']}   ({d['seconds_label']})", fontsize=10.5, color="#2f2e2a")
    ax.text(0.067, 0.18, f"{d['model']} · {d['date']}", fontsize=10.5, color="#6b685f")
    ax.text(0.067, 0.10, "score = killed ÷ (killed + survived)。timeout・suspicious は分母に含めない。n=1 の事例であり一般化しない。",
            fontsize=7.5, color="#8a867a")
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="scorecard image + csv row")
    p.add_argument("--model", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--week", default="01")
    p.add_argument("--label", default="AI生成テストのみ")
    p.add_argument("--note", default="")
    p.add_argument("--coverage", help="coverage.json")
    p.add_argument("--mutmut-log", help="mutmut run の出力")
    p.add_argument("--mutmut-results", help="mutmut results の出力")
    p.add_argument("--seconds", type=int)
    p.add_argument("--seconds-file")
    for k in ("killed", "survived", "timeout", "suspicious"):
        p.add_argument(f"--{k}", type=int, help="ログから拾えないときに直接渡す")
    p.add_argument("--append-csv")
    p.add_argument("--out", default="results/scorecard")
    p.add_argument("--no-image", action="store_true")
    a = p.parse_args()

    text = read_text(a.mutmut_log) + "\n" + read_text(a.mutmut_results)
    counts = parse_counts(text)
    for k in ("killed", "survived", "timeout", "suspicious"):
        override = getattr(a, k)
        if override is not None:
            counts[k] = override
        counts.setdefault(k, 0)

    if not any(counts[k] for k in ("killed", "survived", "timeout", "suspicious")):
        print("WARNING: mutmut の集計を拾えませんでした。--killed 等で直接渡すか STATUS_PATTERNS を確認してください。",
              file=sys.stderr)

    seconds = a.seconds
    if seconds is None and a.seconds_file and Path(a.seconds_file).exists():
        try:
            seconds = int(Path(a.seconds_file).read_text().strip())
        except ValueError:
            seconds = None

    coverage = read_coverage(a.coverage)
    denom = counts["killed"] + counts["survived"]
    score = (counts["killed"] / denom * 100) if denom else None
    total = denom + counts["timeout"] + counts["suspicious"]

    d = {
        "week": a.week, "label": a.label, "date": a.date, "model": a.model,
        "coverage": coverage, "score": score, "total": total,
        "killed": counts["killed"], "survived": counts["survived"],
        "timeout": counts["timeout"], "suspicious": counts["suspicious"],
        "seconds": seconds, "seconds_label": f"mutmut {seconds}s" if seconds is not None else "mutmut —s",
    }

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not a.no_image:
        write_svg(out.with_suffix(".svg"), d)
        png_ok = write_png(out.with_suffix(".png"), d)
        print(f"svg: {out.with_suffix('.svg')}" + (f"\npng: {out.with_suffix('.png')}" if png_ok else "\n(png skipped: matplotlib なし)"))

    if a.append_csv:
        path = Path(a.append_csv)
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if new:
                w.writeheader()
            w.writerow({
                "week": a.week, "label": a.label, "date": a.date, "model": a.model,
                "coverage_pct": "" if coverage is None else f"{coverage:.1f}",
                "mutants_total": total, "killed": counts["killed"], "survived": counts["survived"],
                "timeout": counts["timeout"], "suspicious": counts["suspicious"],
                "score_pct": "" if score is None else f"{score:.1f}",
                "mutmut_seconds": "" if seconds is None else seconds, "note": a.note,
            })
        print(f"csv: {path}")

    print(f"coverage {fmt_pct(coverage)} | score {fmt_pct(score)} | killed {counts['killed']} survived {counts['survived']} "
          f"timeout {counts['timeout']} suspicious {counts['suspicious']} | total {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
