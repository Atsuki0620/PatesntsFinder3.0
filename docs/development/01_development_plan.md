# PatentsFinder3.0 開発プラン

## 1. 開発の目的

本開発プランは、`PatentsFinder2.2`を`3.0`へとアップグレードするための具体的なロードマップを定義する。目的は以下の2点である。
1.  **検索精度の継続的な改善:** UIからロジックを分離し、Gemini CLIを活用した自律的なPDCAサイクル（計画・実行・評価・改善）を導入することで、検索アルゴリズムとパラメータを継続的に最適化する。
2.  **開発・保守性の向上:** システムを「Core（ロジック）」、「Evaluation（評価）」、「UI（表示）」の3層に明確に分離することで、各コンポーネントの独立性を高め、迅速なバグ修正と機能追加を可能にする。

---

## 2. 全体アーキテクチャ

システムは以下の3層構造で構成される。

| レイヤ | 役割 | 主要コンポーネント |
| :--- | :--- | :--- |
| **Core** | 特許検索、類似度計算、要約生成などのコアロジックを担当。純粋なPythonライブラリとして実装。 | `patents_core/` |
| **Evaluation** | Coreロジックの性能を評価し、改善案を生成するPDCAサイクルを実行。 | `evaluation/`, `scripts/` |
| **UI** | ユーザーからの入力受付と、CoreおよびEvaluationの結果を可視化することに特化。 | `app.py` (Streamlit) |

---

## 3. 開発ロードマップ

開発は以下の4つのフェーズで段階的に進める。なお`PatentsFinder2.2`のディレクトリは"C:\Users\atsuk\OneDrive\ドキュメント\GeminiCLI\2507 PatentsFinder2.2"である。

### フェーズ1: 基盤構築（リファクタリング）
- **目標:** 既存の`PatentsFinder2.2`のコードベースを新しい3層アーキテクチャに基づいて分離・整理する。
- **タスク:**
    1.  **ディレクトリ構造の再設計:**
        -   `src/` を `patents_core/` にリネームし、コアロジックを格納。
        -   `evaluation/`、`scripts/`、`tests/` ディレクトリを新規作成。
        -   Streamlitアプリ `app.py` をプロジェクトルート直下に配置。
    2.  **コードの分離:**
        -   `app.py` から、検索や分析に関するロジックをすべて切り出し、`patents_core/` 内のモジュールに移行する。
        -   `app.py` は `patents_core/` の関数を呼び出すだけのシンプルな構成にする。
    3.  **依存関係の整理:**
        -   `requirements.txt` を `patents_core/` 用とプロジェクト全体用に分離・整理する。

### フェーズ2: 評価基盤（Evaluation）の実装
- **目標:** 検索精度の定量的評価を可能にする基盤を構築する。
- **タスク:**
    1.  **評価スクリプトの作成:**
        -   `scripts/run_evaluation.py` を作成。このスクリプトは、定義済みのテストケース（クエリと期待される結果のセット）を実行し、`patents_core` の性能を評価する。
    2.  **評価指標の実装:**
        -   `evaluation/metrics.py` を作成し、適合率（Precision@k）、nDCG@kなどのランク評価指標を計算する関数を実装する。
    3.  **設定の外部化:**
        -   検索ロジックの重みや閾値などのパラメータを `config/weights.yaml` に集約し、外部から変更可能にする。
    4.  **ロギングの強化:**
        -   `loguru` を導入し、評価プロセスの各ステップをJSON形式で詳細にログ出力する。

### フェーズ3: 自律的改善サイクル（Act）の導入
*期間: 3週目*

- **目標:** Gemini CLIを連携させ、評価結果に基づくパラメータの自動チューニングを実現する。
- **タスク:**
    1.  **Gemini CLI連携スクリプトの作成:**
        -   `scripts/suggest_tuning.py` を作成。このスクリプトは、評価結果のログとメトリクスレポートを入力として受け取り、Gemini APIに改善案（`weights.yaml`の修正案）を問い合わせる。
    2.  **改善提案の自動適用:**
        -   Geminiから得られた提案を `weights.yaml` に自動で適用し、再度評価を実行するワークフローを構築する。
    3.  **CI/CD連携:**
        -   GitHub Actionsを設定し、Pull Request時に評価と改善提案のプロセスを自動実行する。

### フェーズ4: UIの高度化と拡張
*期間: 4週目*

- **目標:** 分離されたUIを改善し、分析結果や改善プロセスをユーザーに分かりやすく提示する。
- **タスク:**
    1.  **UIの改善:**
        -   `app.py` を見直し、`patents_core` からの結果表示をより洗練させる。
    2.  **評価結果の可視化:**
        -   過去の評価結果（メトリクスの推移など）を可視化するダッシュボードページをStreamlit上に追加する。
    3.  **将来拡張への準備:**
        -   RAGAs指標の導入や、A/Bテスト実施のための基盤を設計・準備する。

---

## 4. 新しいディレクトリ構造（案）

```
.
├── app.py                      # Streamlit UI
├── config/
│   └── weights.yaml            # 検索ロジックの重み・パラメータ
├── evaluation/
│   ├── gold_standard.jsonl     # 評価用の正解データセット
│   └── metrics.py              # 評価指標を計算するモジュール
├── logs/
│   └── evaluation_log.jsonl    # 評価実行ログ
├── patents_core/
│   ├── __init__.py
│   ├── agent.py
│   ├── state.py
│   ├── tools.py
│   └── utils/
│       └── config.py
├── reports/
│   └── metrics_report.json     # 最新の評価結果レポート
├── scripts/
│   ├── run_evaluation.py       # 評価実行スクリプト
│   └── suggest_tuning.py       # Gemini CLI連携による改善提案スクリプト
├── tests/
│   ├── test_core_logic.py
│   └── test_evaluation.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 5. 次のステップ

本開発プランの承認後、速やかに **フェーズ1: 基盤構築（リファクタリング）** に着手する。
最初のタスクとして、提案された新しいディレクトリ構造を作成し、既存コードの移行を開始する。
