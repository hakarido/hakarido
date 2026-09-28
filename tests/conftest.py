"""通常の pytest 実行時だけ src/ を import パスに入れる。

mutmut の実行中（環境変数 MUTANT_UNDER_TEST がある）は何もしない。mutmut は mutants/src を自分で sys.path に入れ、
元の src/ を外す。ここで src/ を足すと元のコードがテストされて全ミュータントが「no tests」になる
（mutmut 3.8 の _check_test_to_mutant_associations が指摘する「conftest sys.path injection」）。

テストは `from target import ...` と書く（`from src.target import` ではない。mutmut は "src." を剥がした
モジュール名で記録するため）。
"""
import os
import sys
from pathlib import Path

if "MUTANT_UNDER_TEST" not in os.environ:
    SRC = Path(__file__).resolve().parents[1] / "src"
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
