# PatentsFinder 3.0

## 概要

**PatentsFinder 3.0** は、大規模言語モデル（LLM）を活用して、自然言語による対話形式で特許調査を行えるWebアプリケーションです。Google BigQueryの公開特許データセットを検索し、Streamlitで構築されたUIを通じて、検索結果の分析、要約、評価を行います。

このプロジェクトの最大の特徴は、**RAGAs評価フレームワークを導入**し、検索・要約ロジックの品質を定量的に評価する基盤を構築している点です。将来的には、この評価結果をフィードバックとしてLLM自身が改善案を考え、コードを修正していく**自律的なPDCAサイクル**の実現を目指しています。

## 主な機能

*   **対話形式の特許検索:** 自然言語で質問するだけで、AIが調査方針を立案し、検索クエリを自動生成します。
*   **高度な検索ロジック:** Google BigQueryの強力な検索能力を活用し、IPCコード、キーワード、出願��などで特許を絞り込みます。
*   **AIによる結果分析と要約:** 検索結果を調査方針との関連性に基づいてランキングし、重要な特許の要点をまとめたサマリーを生成します。
*   **RAGAsによる品質評価:** 生成された回答の品質を「忠実性（Faithfulness）」や「関連性（Answer Relevancy）」といった指標で自動評価します。
*   **自律的改善サイクル基盤:** 評価スコアを元に、改善提案から実装までを自動化する将来的な拡張性を備えています。

## システム構成

*   **フロントエンド:** Streamlit
*   **バックエンド:** Python, LangGraph, LangChain
*   **LLM:** OpenAI API (GPT-4o)
*   **データベース:** Google BigQuery (`patents-public-data.patents.publications`)
*   **評価フレームワーク:** RAGAs

## ディレクトリ構造

```
.
├── app.py                     # Streamlitアプリケーション本体
├── patents_core/              # 中核ロジック（エージェント、ツールなど）
│   ├── core/
│   │   ├── agent.py           # LangGraphを用いたワ���クフロー定義
│   │   ├── state.py           # 状態管理クラス
│   │   └── tools.py           # BigQuery検索ツール
│   └── utils/
├── evaluation/                # RAGAs評価関連
│   ├── gold_standard.jsonl    # 評価用テストデータ
│   └── metrics.py             # 評価指標の計算ロジック
├── scripts/                   # 各種スクリプト
│   └── run_evaluation.py      # 評価実行スクリプト
├── config/                    # 設定ファイル
├── requirements.txt           # 依存ライブラリ
└── README.md                  # このファイル
```

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/Atsuki0620/PatesntsFinder3.0.git
cd PatesntsFinder3.0
```

### 2. Python仮想環境の作成と有効化

```bash
# Windows
python -m venv env-PatentsFinder3.0
.\env-PatentsFinder3.0\Scripts\activate
```

### 3. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env.example` を参考に `.env` ファイルを作成し、以下のAPIキーを設定してください。

```
# .env
OPENAI_API_KEY="sk-..."
GOOGLE_APPLICATION_CREDENTIALS="path/to/your/gcp-credentials.json"
```

`GOOGLE_APPLICATION_CREDENTIALS` には、Google Cloud Platformで取得したサービスアカウントのJSONキーファイルへのパスを指定します。

## 実行方法

### Webアプリケーションの起動

```bash
streamlit run app.py
```

### 品質評価の実行

```bash
python scripts/run_evaluation.py
```

評価結果は `reports/metrics_report.json` に出力されます。

## ライセンス

This project is licensed under the MIT License.
