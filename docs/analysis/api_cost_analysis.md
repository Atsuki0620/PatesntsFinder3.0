# APIコスト分析レポート (PatentsFinder 3.0 改善サイクル) - 更新版

このレポートは、PatentsFinder 3.0の1回の改善サイクル（`scripts/run_evaluation.py`の実行）で発生するAPI利用料金の概算をまとめたものです。
**直前の改善サイクル（answer_relevancy改善後）のログに基づき、数値を更新しました。**

**【重要】**
このレポートの数値は、現在のコードと評価データ（1件）に基づいた**概算値**です。実際の料金は、検索クエリの内容、検索結果の件数や内容、OpenAIのモデルや料金の改定によって変動します。正確な料金は各サービスのダッシュボードで確認してください。

## 1. 分析対象API

分析対象のAPIは以下の通りです。

*   **Google BigQuery API:** 特許データの検索
*   **OpenAI API:**
    *   Embeddingモデル (`text-embedding-3-small`): 検索結果の分析
    *   LLM (`gpt-4o`): 要約生成、RAGAsによる評価

## 2. コスト概算サマリー（テストケース1件あたり）

| API           | サービス (モデル)             | 用途             | 概算使用量 (Tokens / Data) | 概算料金 (USD) | 備考                               |
| :------------ | :---------------------------- | :--------------- | :------------------------- | :------------- | :--------------------------------- |
| Google BigQuery | On-Demand Query               | 特許検索         | 約 100 MB (仮定)           | ~$0.0006       | 検索条件により大きく変動           |
| OpenAI        | `text-embedding-3-small`      | 検索結果の分析   | 約 3,500 Tokens            | ~$0.0000005    | ほぼゼロ                           |
| OpenAI        | `gpt-4o`                      | 要約レポート生成 | In: ~3,500, Out: **~2,300** | **~$0.0520**   | **品質向上のため出力が増加**       |
| OpenAI        | `gpt-4o` (via RAGAs)          | 品質評価         | In: **~6,000**, Out: ~100   | **~$0.0315**   | **要約出力の増加に伴い入力も増加** |
| **合計**      |                               |                  |                            | **~$0.0841**   |                                    |

**結論：現状のテストケース1件を実行するごとのAPIコストは、約 $0.084 USD (約12.2円 ※) と試算されます。**
これはプロンプト改善前の試算（約$0.038）から倍以上に増加しています。主な要因は、`answer_relevancy`向上のためにプロンプトを修正した結果、生成される要約レポートがより詳細になり、出力トークン数が大幅に増加したためです。

※ 1ドル=145円で換算

## 3. コスト詳細内訳

### 3.1. Google BigQuery

*   **呼び出し箇所:** `patents_core/core/tools.py` の `search_patents_in_bigquery`
*   **料金モデル:** オンデマンドクエリ ($6.00 per TB)
*   **内訳:**
    *   1回のクエリで **100 MB** のデータをスキャンすると仮定。
    *   **計算:** `$6.00 / 1 TB * (100 MB / 1,000,000 MB/TB) = $0.0006`

### 3.2. OpenAI API

#### a. Embedding生成 (`text-embedding-3-small`)

*   **呼び出し箇所:** `patents_core/core/agent.py` の `analyze_results`
*   **料金単価:** $0.13 / 1M tokens
*   **内訳:**
    *   検索結果5件の分析のため、約 **3,500 トークン**を生成。
    *   **計算:** `($0.13 / 1,000,000) * 3,500 = $0.000000455` (コストへの影響は無視できるレベル)

#### b. 要約レポート生成 (`gpt-4o`)

*   **呼び出し箇所:** `patents_core/core/agent.py` の `summarize_selected_patents`
*   **料金単価:** Input: $5.00 / 1M tokens, Output: $15.00 / 1M tokens
*   **内訳:**
    *   **概算入力トークン数:** 約 **3,500 トークン** (プロンプト + 調査方針 + 特許リスト5件)
    *   **概算出力トークン数:** **約 2,300 トークン** (ログに基づき再計算。以前の800から増加)
    *   **計算:**
        *   Input: `($5.00 / 1,000,000) * 3,500 = $0.0175`
        *   Output: `($15.00 / 1,000,000) * 2,300 = $0.0345`
        *   **合計: $0.052**

#### c. RAGAsによる品質評価 (`gpt-4o`)

*   **呼び出し箇所:** `evaluation/metrics.py` の `evaluate_with_ragas`
*   **料金単価:** Input: $5.00 / 1M tokens, Output: $15.00 / 1M tokens
*   **内訳:**
    *   **`faithfulness`評価:**
        *   入力: `answer` (約2,300) + `contexts` (約1,300) = **約3,600 トークン**
    *   **`answer_relevancy`評価:**
        *   入力: `question` (約100) + `answer` (約2,300) = **約2,400 トークン**
    *   **計算:**
        *   Input: `($5.00 / 1,000,000) * (3600 + 2400) = $0.03`
        *   Output: `($15.00 / 1,000,000) * (50 + 50) = $0.0015`
        *   **合計: $0.0315**

## 4. 総コストとコスト削減の提案

### 総コスト

**総コスト = (1件あたりのコスト: $0.084) x (テストケース数)**

例えば、テストケースが10件あれば、1回の評価実行で約 $0.84 USD の費用が発生します。品質とコストはトレードオフの関係にあることを認識する必要があります。

### コスト削減の提案

1.  **評価モデルの変更:**
    *   RAGAsの評価や要約生成に、より安価なモデル（例: `gpt-3.5-turbo`）を利用できないか検討します。ただし、評価スコアや要約の品質が低下する可能性があります。
2.  **開発中の評価データ削減:**
    *   機能開発中は、`gold_standard.jsonl` の内容を1件に絞って実行することで、試行錯誤のコ���トを最小限に抑えられます。（現在実践中）
3.  **BigQueryのコスト最適化:**
    *   より限定的な `WHERE`句（特に日付やIPCコード）を指定し、スキャンするデータ量を削減することが最も効果的です。
4.  **要約内容の調整:**
    *   プロンプトを調整し、各項目の説明をより簡潔にするよう指示することで、出力トークン数を削減できる可能性があります。ただし、`answer_relevancy`スコアへの影響を注視する必要があります。

以上が、APIコストの再計算結果です。