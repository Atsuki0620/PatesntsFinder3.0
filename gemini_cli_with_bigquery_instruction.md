# Gemini CLI 指示書：自動検索評価・改善システムの構築（BigQuery連携付き）


## 背景
PrantsFinderのアップグレードの開発作業において、ユーザーの調査意図にマッチした検索結果が得られていないことが問題となっています。

---

## 🎯 目的
ユーザーの検索意図と一致する特許検索結果を自律的に出力・評価・改善するシステムを、BigQuery連携を含めてPythonスクリプトとして構築してください。これまでは、私から指示→Gemini cliがアップグレード作業→streamlitアプリを立ち上げて私自身でテスト→アプリ画面上のエラーメッセージをコピペしてGemini cliに返す→エラー部分修正→繰り返し、という流れで開発してきました。また検索結果がユーザーの調査意図にマッチしないという課題もある。これだとエラー検知はstreamlitアプリを介して人間が行なっているので、AIエージェント（Gemini cli）で自律的にエラー検知して改善するサイクルが回せてない。

---

## 備考
- BigQueryによる事前検索が実装プロセスに必須
- 各ファイルの責任範囲を分離し、テストから自動評価・再実行まで「自律サイクル」を実現
- 各コードは用途別に関数やコメント付きで記述
- PatentsFinder2.2に合わせた現場実装イメージに仕上げ

---

## ✅ 実装すべき構成

以下のフォルダ構成に従ってファイルを生成し、必要なロジックをすべてPythonで記述してください。

```
/tests
├── test_queries.yaml     # クエリとGold Setの定義
├── test_runner.py        # BigQuery → Gemini CLI 実行 → ログ保存
├── evaluator.py          # Gold Setと出力の評価（類似度計算）
├── fixer.py              # 再実行プロンプトの生成
/logs
└── results.json          # 評価スコア・再実行履歴などのログ
```

---

## 🧩 各ファイルの要件

### 1. test_queries.yaml
- YAML形式で複数のクエリ、検索意図（intent）、期待される特許番号（Gold Set）を定義

例：
```yaml
queries:
  - query: "逆浸透膜の劣化検知"
    intent: "RO膜の劣化に関する特許を幅広く抽出したい"
    gold_set:
      - JP2020123456A
      - JP2019123456B
```

---

### 2. test_runner.py
- 各クエリに対し以下を自動実行：

#### ✅ BigQuery検索（タイトルにキーワード含む特許）
```sql
SELECT publication_number
FROM `patents.patents_publications`
WHERE LOWER(title) LIKE '%<クエリ>%'
LIMIT 10
```

#### ✅ Gemini CLI実行
- BigQueryの検索結果とユーザーの意図を組み合わせて、検索結果を出力

#### ✅ 評価と再実行
- `evaluator.py`を用いてGold Setとの一致スコアを算出
- スコア < 0.75 の場合、`fixer.py`で再プロンプト生成 → Gemini CLI再実行（最大2回）

#### ✅ ログ出力
- クエリ、出力、スコア、再実行回数、プロンプト履歴を`../logs/results.json`に保存

---

### 3. evaluator.py
- 出力結果とGold Setとの一致度を計算
- 可能であればOpenAI Embeddingを用いたcosine類似度を評価指標とする

---

### 4. fixer.py
- 検索精度が低い場合に、Gemini CLIに次のようなプロンプトを渡す：

```
前回の出力は意図（<intent>）に対し、次の理由でマッチ度が低いです：
- 不足・過剰な特許候補: <差分>
上記を考慮し、再検索してください。
```

---

## 📝 出力ログ：results.json（例）

```json
[
  {
    "query": "逆浸透膜の劣化検知",
    "gold_set": ["JP2020123456A", "JP2019123456B"],
    "bq_results": ["JP2020123456A", "JP2018123456C"],
    "gemini_results": ["JP2020123456A", "JP2018123456C"],
    "score": 0.5,
    "retry_count": 1,
    "prompts_history": ["..."]
  }
]
```

---

## 💡 補足条件
- すべてのスクリプトはCLIから実行可能であること
- 必要な外部ライブラリがある場合は `requirements.txt` に記載

---

## ✅ 完了条件
- 上記構成の全ファイルを生成し、Pythonコードをすべて自動化
- Gemini CLI が人の手を介さず、出力→評価→改善サイクルを実現すること
