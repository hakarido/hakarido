# ハーネス v0 — 「AIコードを測って壊す」週1計測の起点

週1本の元ネタ（表・スクショ・再現リポジトリ・「想定と違ったこと」）を、毎週同じ手順で出すためのひな形。
`hakarido` は確定したハンドル名に一括置換する（CLI名・PyPI名・GitHub名と同じ文字列）。

**動かす場所：WSL2（Ubuntu）**。mutmut 3.8 は Windows ネイティブでは起動時に「To run mutmut on Windows, please use the WSL.」と出て終了する（2026-09-28 に実機で確認）。ハンドル名の別OSユーザーで使う。

mutmut 3.8 の動き（ソースで確認済み）：`mutants/` に `src/` と `also_copy`（tests/・pyproject.toml）をコピーし、`mutants/` を作業ディレクトリにして pytest を回す。`mutants/src` を sys.path に入れ、元の `src/` を外す。ミュータント名は `target.x_関数名__mutmut_N`（`src.` は剥がされる）。だからテストは `from target import ...` と書き、conftest は mutmut 実行中は sys.path を触らない。

## 構成

```
harness_v0/
  pyproject.toml            pytest / coverage / mutmut 3系の設定
  Makefile                  make bench / cov / mutmut / card / classify / canary / lint / env
  src/target.py             週1の対象モジュール（依存なし純粋関数、約150行、MIT）
  tests/conftest.py         import パス
  tests/test_smoke.py       ハーネスの動作確認用。★週1の生成前に削除する
  prompts/week01.md         固定プロンプト（カナリアも同じ文面を使う）
  scripts/scorecard.py      1枚画像（行カバレッジ／スコア／モデル／日付）＋CSV 1行追記
  scripts/classify_survivors.py  生存ミュータントの規則ベース一次分類＋抜き取り検証欄
  scripts/canary.sh         固定プロンプト→生成→coverage→mutmut→results/canary.csv に1行（無人）
  scripts/env_capture.py    環境欄の情報（ホスト名・ユーザー名は集めない）
  scripts/setup_wsl2.sh     WSL2 に一式を入れて動作確認
  bench/lint_all.py         週4用：静的解析の検出密度（100行あたり）
  results/                  CSV のスキーマと出力先
  .github/ISSUE_TEMPLATE/different_result.md  「別の結果が出た」テンプレ
  README_TEMPLATE.md        毎週の公開リポジトリ用 README のひな形
  LICENSE                   MIT
```

## 初回（1回だけ・約20分）

```
bash scripts/setup_wsl2.sh        # venv 作成、pytest/coverage/mutmut/hypothesis/ruff/mypy/bandit/radon/matplotlib、日本語フォント
. .venv/bin/activate
make cov                          # test_smoke.py で coverage が出るか
make mutmut                       # mutants/ が作られ、[tool.mutmut] が読めているか（対象0件でないこと）
python scripts/scorecard.py --model test --date 2026-01-01 --week 00 \
  --coverage results/coverage.json --mutmut-log results/mutmut_run.log \
  --mutmut-results results/mutmut_results.txt --out results/scorecard_test
```
`results/scorecard_test.svg` の killed / survived が `mutmut results` の表示と一致していることを**目視で確認**する。mutmut の表示形式はバージョンで違うので、拾えていなければ `scripts/scorecard.py` の `STATUS_PATTERNS` を直すか、`--killed` 等で直接渡す。

## 週1の流れ（本人35分の内訳は THEME_AND_HANDLE.md 第4節）

1. `git rm tests/test_smoke.py`（AI生成テスト以外を残さない）
2. `src/target.py` を読んで確定（前夜にAIが下書き→本人が読む。仕様を変えたら docstring も直す）
3. Claude Code で `prompts/week01.md` の文面をそのまま渡す。生成物は `tests/test_ai_generated.py` にだけ入る。**無改変でコミット**（`git commit -m "week01: AI-generated tests, unmodified"`）。モデル名・日付・再指示回数を `prompts/week01.md` の先頭欄に記入
4. `MODEL="<モデル名>" WEEK=01 make bench` → coverage → mutmut → env → スコアカード → 生存ミュータントの一次分類
5. `results/survivors_week01.csv` から10件を抜き取り、`human_checked` と `human_category` を埋める
6. 生存上位1種を殺すテストを5分で `tests/test_human_added.py` に書き、`LABEL="＋人間追加" WEEK=01 make cov mutmut card`
7. `results/week01.csv`（2行）、`results/scorecard_week01.svg/png`、スクショ3点（coverage 100%／mutmut summary／survived 一覧）を記事へ
8. `MODEL="<モデル名>" make canary` を1回回し、`results/canary.csv` に初回の1行が入ることを確認（以後は毎週1回）

## 定義（記事にも毎回書く）

- **ミューテーションスコア% = killed ÷ (killed + survived) × 100**。timeout と suspicious は分母に入れず別掲する。
- 行カバレッジは `pytest --cov=src` の `totals.percent_covered`。
- n は「同じプロンプトで生成した回数」。週1は n=1 と明記し、統計的な主張はしない（週5で分散を測るまで）。

## 公開前の確認（毎回）

- スクショ・録画に `~/`、ユーザー名、ホスト名、通知、別ウィンドウが映っていない
- `results/env.txt` にホスト名・ユーザー名・パスが無い（`env_capture.py` は集めないが、目視でも確認）
- 実名 GitHub へのリンク、コミットハッシュの参照が無い
- 生成物 `tests/test_ai_generated.py` が無改変（`git log -p` で示せる）

## カナリアについて

`scripts/canary.sh` は Claude Code を非対話（`claude -p`）で起動し、一時ディレクトリの中だけに書き込ませる。Pro の利用枠を消費するので、週1回・1実行に留める。実行は本人が行う（タスクスケジューラ等での自動起動は、4週連続で欠測したときにだけ検討する）。
