# hakarido ハーネス v0
#   make bench            coverage → mutmut → env → scorecard → 生存ミュータント分類
#   make cov / mutmut     個別に
#   make card             results/ の既存結果からスコアカードだけ作り直す
#   make canary           固定プロンプトで無人1回（results/canary.csv に1行）
#   make lint LABEL=AI DIR=corpus_ai     週4用の静的解析密度
# 変数: MODEL="生成に使ったモデル名"  WEEK=01  LABEL="AI生成テストのみ"  DATE=YYYY-MM-DD
# 後片付け: mutants/ .mutmut-cache .coverage .pytest_cache は手で削除する（このMakefileは削除コマンドを持たない）

PY    ?= python
MODEL ?= unknown
DATE  ?= $(shell date +%F)
WEEK  ?= 01
LABEL ?= AI生成テストのみ
NOTE  ?=

.PHONY: bench test cov mutmut env card classify canary lint

test:
	$(PY) -m pytest -q

cov:
	@mkdir -p results
	$(PY) -m pytest -q --cov=src --cov-report=term-missing --cov-report=json:results/coverage.json

mutmut:
	@mkdir -p results
	@start=$$(date +%s); mutmut run 2>&1 | tee results/mutmut_run.log; end=$$(date +%s); echo $$((end-start)) > results/mutmut_seconds.txt
	-mutmut results > results/mutmut_results.txt 2>&1

env:
	@mkdir -p results
	$(PY) scripts/env_capture.py --model "$(MODEL)" --date "$(DATE)" --out results/env.txt

card:
	$(PY) scripts/scorecard.py --model "$(MODEL)" --date "$(DATE)" --week "$(WEEK)" --label "$(LABEL)" --note "$(NOTE)" \
	  --coverage results/coverage.json --mutmut-log results/mutmut_run.log \
	  --mutmut-results results/mutmut_results.txt --seconds-file results/mutmut_seconds.txt \
	  --append-csv results/week$(WEEK).csv --out results/scorecard_week$(WEEK)

classify:
	$(PY) scripts/classify_survivors.py --results results/mutmut_results.txt --out results/survivors_week$(WEEK).csv

bench: cov mutmut env card classify

canary:
	MODEL="$(MODEL)" bash scripts/canary.sh

lint:
	@mkdir -p results
	$(PY) bench/lint_all.py --label "$(LABEL)" "$(DIR)" --out results/lint.csv
