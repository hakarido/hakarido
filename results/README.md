# results/ — 出力先と CSV のスキーマ

生データは捨てない。記事の表はここから転記し、note の有料付属物にはこのフォルダの CSV をそのまま入れる。

| ファイル | 誰が書く | 中身 |
|---|---|---|
| `coverage.json` | `make cov` | pytest-cov の JSON。`totals.percent_covered` を使う |
| `mutmut_run.log` / `mutmut_results.txt` / `mutmut_seconds.txt` | `make mutmut` | 実行ログ・結果一覧・実行秒 |
| `env.txt` | `make env` | 環境欄（ホスト名・ユーザー名は含まない） |
| `weekNN.csv` | `make card`（1行ずつ追記） | スコアカードの元データ。下のスキーマ |
| `scorecard_weekNN.svg / .png` | `make card` | X に貼る1枚画像 |
| `survivors_weekNN.csv` | `make classify` | 生存ミュータントの一次分類＋抜き取り検証欄 |
| `canary.csv` | `make canary` | 固定プロンプトの週次値（weekNN.csv と同じ列、label=canary） |
| `lint.csv` | `make lint` | 週4の静的解析密度 |

## weekNN.csv / canary.csv の列

```
week,label,date,model,coverage_pct,mutants_total,killed,survived,timeout,suspicious,score_pct,mutmut_seconds,note
```
- `label`：`AI生成テストのみ` ／ `＋人間追加` ／ `canary`
- `score_pct` = killed ÷ (killed + survived) × 100（timeout・suspicious は分母に入れない）

## 記事の表（week_schema.csv）の列

```
週,対象モジュール,行数,行カバレッジ%,ミュータント総数,killed,survived,timeout,suspicious,ミューテーションスコア%,生存上位種別1,件数1,生存上位種別2,件数2,生存上位種別3,件数3,人間追加後スコア%,追加テスト数,mutmut実行秒,モデル名,計測日,再指示回数
```
