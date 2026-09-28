#!/usr/bin/env bash
# canary.sh — 固定プロンプト（prompts/week01.md）で週1回・無人で
#   テスト生成 → coverage → mutmut → results/canary.csv に1行 を行う。
# 本人がやるのは起動と、csv に1行増えたことの確認（2分）。
#
# 使い方:  MODEL="Claude Code / <モデル名>" bash scripts/canary.sh
# 前提:   .venv を有効化済み、claude コマンドが PATH にある、Pro の枠を1回分使う
# 書き込み先: mktemp で作った一時ディレクトリの中だけ（リポジトリ本体には results/canary.csv 以外触らない）
# 片付け:  一時ディレクトリは /tmp に残る（削除コマンドはこのスクリプトに入れていない。OS の /tmp 掃除に任せるか手で消す）
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="${MODEL:-unknown}"
DATE="$(date +%F)"
WORK="$(mktemp -d -t canary-"$DATE"-XXXXXX)"
mkdir -p results

# 固定プロンプト本文（--- より下）を取り出す
PROMPT="$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' prompts/week01.md)"

# 対象と設定だけを一時ディレクトリへ（テストは空の状態から生成させる）
cp -r src pyproject.toml "$WORK"/
mkdir -p "$WORK/tests" "$WORK/prompts"
cp tests/conftest.py "$WORK/tests/"
cp prompts/week01.md "$WORK/prompts/"

echo "[canary] work dir: $WORK"
echo "[canary] model: $MODEL  date: $DATE"

# 非対話で生成。書き込みは一時ディレクトリ内のみ。pytest の実行だけ許可する。
(
  cd "$WORK"
  claude -p "$PROMPT" \
    --permission-mode acceptEdits \
    --allowedTools "Bash(python -m pytest:*),Bash(pytest:*)" \
    --max-turns 30 > claude.log 2>&1 || true
)

if [ ! -f "$WORK/tests/test_ai_generated.py" ]; then
  echo "week01,canary,$DATE,$MODEL,,,,,,,,,generation_failed" >> results/canary.csv
  echo "[canary] 生成物がありません（$WORK/claude.log を確認）"
  exit 0
fi

(
  cd "$WORK"
  python -m pytest -q --cov=src --cov-report=json:coverage.json > pytest.log 2>&1 || true
  start=$(date +%s)
  mutmut run > mutmut_run.log 2>&1 || true
  mutmut results > mutmut_results.txt 2>&1 || true
  echo $(( $(date +%s) - start )) > mutmut_seconds.txt
)

python scripts/scorecard.py --model "$MODEL" --date "$DATE" --week 01 --label canary \
  --coverage "$WORK/coverage.json" --mutmut-log "$WORK/mutmut_run.log" \
  --mutmut-results "$WORK/mutmut_results.txt" --seconds-file "$WORK/mutmut_seconds.txt" \
  --append-csv results/canary.csv --out "$WORK/scorecard" --no-image

echo "[canary] 追記しました → results/canary.csv（生成物・ログは $WORK）"
