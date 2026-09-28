# 固定プロンプト week01（カナリアも毎週この文面をそのまま使う）

記録欄（本人が実行のたびに記入。プロンプト本文は変えない）
- モデル名・バージョン：
- 実行日：
- ツール（Claude Code のバージョン）：
- 再指示回数（100%未達で再指示した回数）：
- 生成にかかった時間（分）：

---

以下がAIに渡す本文。`---` より下を一字も変えずに貼る。

---

`src/target.py` のテストを `tests/test_ai_generated.py` に書いてください。

条件：
- pytest を使う。標準ライブラリと pytest 以外は使わない。
- import は `from target import ...` と書く（`tests/conftest.py` が `src/` を通す。`src.target` とは書かない）。
- `python -m pytest --cov=src` の行カバレッジが 100% になること。
- `src/target.py` は変更しない。`tests/test_ai_generated.py` 以外のファイルを作らない・変更しない。
- 各テスト関数の先頭に、何を検証するかを1行の docstring で書く。
- 書き終えたら実行して 100% を確認し、最後にカバレッジの数値だけを報告する。
