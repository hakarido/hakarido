#!/usr/bin/env bash
# setup_wsl2.sh — WSL2 (Ubuntu) に週1ハーネスの環境を作り、動作確認まで行う。
# ハンドル名の OS ユーザーで、リポジトリ直下から実行する:  bash scripts/setup_wsl2.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== apt"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git make fonts-noto-cjk

echo "== venv"
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install --upgrade pip
pip install pytest pytest-cov coverage mutmut hypothesis ruff mypy bandit radon matplotlib

echo "== versions"
python --version
python -m pytest --version
mutmut --version 2>/dev/null || mutmut version 2>/dev/null || echo "(mutmut のバージョン表示コマンドは版により異なる)"

echo "== git identity（実名を入れない。noreply アドレスの ID 付き形式は GitHub の Emails 設定画面で確認して置き換える）"
git config user.name "hakarido" 2>/dev/null || true
git config user.email "hakarido@users.noreply.github.com" 2>/dev/null || true

echo "== smoke: coverage"
mkdir -p results
python -m pytest -q --cov=src --cov-report=term-missing --cov-report=json:results/coverage.json

echo "== smoke: mutmut（[tool.mutmut] が読めて mutants/ ができ、対象が0件でないことを確認）"
mutmut run 2>&1 | tee results/mutmut_run.log || true
mutmut results 2>&1 | tee results/mutmut_results.txt || true

echo "== smoke: scorecard"
python scripts/scorecard.py --model "setup-test" --date "$(date +%F)" --week 00 \
  --coverage results/coverage.json --mutmut-log results/mutmut_run.log \
  --mutmut-results results/mutmut_results.txt --out results/scorecard_setup_test

echo
echo "確認すること:"
echo "  1. 上の scorecard の killed / survived が 'mutmut results' の表示と一致しているか（違えば scripts/scorecard.py の STATUS_PATTERNS を直す）"
echo "  2. results/scorecard_setup_test.png の日本語が豆腐になっていないか（fonts-noto-cjk が入っていれば出る）"
echo "  3. 週1の計測前に tests/test_smoke.py を削除する"
