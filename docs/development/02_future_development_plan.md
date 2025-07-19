# PatentsFinder3.0 今後の開発プラン（内部ロジック優先）

本プランは、`PatentsFinder3.0`の内部ロジックと基盤の強化に特化し、UIの作り込みや編集はスコープ外とします。

## 1. 開発の目的

評価基盤が確立された`PatentsFinder3.0`において、Gemini CLIを活用した自律的なPDCAサイクルを完成させ、検索精度の継続的な自動改善を実現します。また、テストの網羅性を高め、コアロジックのさらなる洗練を目指します。LLMにはOpenAI APIを利用し、APIキーは`.env`ファイルを参照します。

## 2. ロードマップ

### フェーズ3: 自律的改善サイクル（Act）の完成

-   **目標:** 評価結果に基づいたGemini APIによる自動チューニング提案を実装し、PDCAサイクルを機能させる。
-   **タスク:**
    1.  **Gemini API連携の実装:**
        -   `scripts/suggest_tuning.py`内のダミー実装を、実際のGemini API呼び出しロジックに置き換える。
        -   評価レポート（`reports/metrics_report.json`）と詳細ログ（`logs/evaluation_log.jsonl`）をプロンプトに含め、`weights.yaml`の最適な調整案をGeminiに生成させる。この際、評価指標としてRAGAsのスコアを考慮する。
        -   Geminiからの応答をパースし、`scripts/apply_tuning.py`が利用できる形式で出力する。

### フェーズ5: テストとロジックの洗練

-   **目標:** RAGAsを用いた評価の信頼性を高め、コアロジックの性能を継続的に向上させる。
-   **タスク:**
    1.  **RAGAs評価基盤の導入:**
        -   `evaluation/metrics.py`をRAGAsライブラリを利用するように再実装する。
        -   `scripts/run_evaluation.py`を更新し、RAGAsの評価指標を計算・出力するように変更する。
        -   RAGAsの評価に必要な追加データ（例: 質問、コンテキスト、回答、グラウンドトゥルース）を`evaluation/gold_standard.jsonl`または別のファイルで管理できるよう、データ形式を検討・調整する。
    2.  **テストケースの拡充:**
        -   `evaluation/gold_standard.jsonl`に、より多様で複雑な検索シナリオをカバーするテストケースを追加する。
        -   異なる技術分野、キーワードの組み合わせ、IPCコードのバリエーション、公開日範囲などを考慮したテストデータを整備する。
        -   RAGAsの評価に必要な質問、コンテキスト、期待される回答などの情報を充実させる。
    3.  **評価結果の分析とロジック改善:**
        -   `reports/metrics_report.json`と`logs/evaluation_log.jsonl`のRAGAs指標の詳細な分析に基づき、`patents_core`内の検索ロジック（`patents_core/core/tools.py`）、類似度計算アルゴリズム（`patents_core/core/agent.py`）、および要約生成ロジック（`patents_core/core/agent.py`）の改善点を特定する。
        -   必要に応じて、LLMプロンプトの最適化、新しい情報検索技術（例: RAGの高度化、再ランキング手法）の導入を検討・実装する。

## 3. 成果物

-   `scripts/suggest_tuning.py`のGemini API連携実装
-   RAGAs評価基盤（`evaluation/metrics.py`の更新、`scripts/run_evaluation.py`の更新）
-   RAGAs評価に対応した`evaluation/gold_standard.jsonl`の拡充
-   改善された`patents_core`内のロジックコード

## 4. 次のステップ

まずは、**フェーズ5の「RAGAs評価基盤の導入」**に着手します。