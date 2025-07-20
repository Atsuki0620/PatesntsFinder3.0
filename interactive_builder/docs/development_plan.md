# 対話型・PatentsFinder検索ロジック強化 開発計画書

## 1. 概要・目的

### 1.1. 開発の背景
現在の`run_investigation.py`は、一度の対話で得た情報からキーワードとIPCを抽出し、固定的なロジックでSQLを生成している。このアプローチでは、ユーザーの複雑な調査意図を正確に反映できず、結果の関連性が低くなる問題があった。

### 1.2. 目的
本プロジェクトの目的は、**PatentsFinderの検索精度を抜本的に向上させること**である。そのために、J-PlatPatの専門的な検索手法を参考に、AIとの対話を通じて検索条件を段階的に精緻化する新しいインターフェースを開発する。最終的なゴールは、ユーザーの意図を正確に反映した`SearchQuery`オブジェクトを構築し、それを用いて**PatentsFinderの既存の検索ワークフローを実行**することにある。

## 2. 主要機能

1.  **対話による検索条件の段階的な精緻化:**
    *   調査目的、主題、関連技術、特許分類（IPC）、絞り込み条件などを段階的にヒアリングし、検索の全体像を明確化する。

2.  **AIによる知識補助:**
    *   **キーワード拡張:** ユーザーが提示したキーワードに対し、類義語、同義語、表記ゆれ、英語表現などをAIが提案し、検索漏れを防ぐ。
    *   **特許分類（IPC）の提案:** キーワードに基づき、関連性の高いIPCをAIがサジェストする。
    *   **検索ロジックの提案:** 収集した条件をどのように組み合わせるか（AND/OR）、最適な論理構造をAIが提案する。

3.  **状態の可視化と反復的な修正:**
    *   対話の各ステップで、現在構築されている検索条件の全体像をユーザーに提示し、いつでも修正や追加ができるようにする。

4.  **既存ワークフローとのシームレスな統合:**
    *   対話の最終結果として、PatentsFinderが解釈できる`SearchQuery`オブジェクトを生成し、既存の検索・分析ワークフローを直接呼び出す。

## 3. ディレクトリ構成

```
interactive_builder/
├── builder.py             # 対話フローと既存ワークフローの連携を実行するメインスクリプト
├── docs/
│   └── development_plan.md  # この開発計画書
└── core/
    ├── state.py             # 対話の状態を管理するSearchContextクラス
    ├── prompts.py           # AIとの対話で用いるプロンプトテンプレート群
    └── query_converter.py   # SearchContextからSearchQueryへの変換ロジック
```

## 4. 主要コンポーネントとロジック設計

### 4.1. `core/state.py`: 対話状態の管理
対話の途中経過を保持する`SearchContext`クラスを定義する。

```python
class SearchContext:
    def __init__(self):
        self.purpose: str = ""
        self.main_keywords: list[str] = []
        self.related_keyword_groups: list[list[str]] = []
        self.ipc_codes: list[str] = []
        self.date_range: str = ""
        self.applicants: list[str] = []
```

### 4.2. `core/prompts.py`: AIへの指示
対話の各ステップで用いるプロンプトを集中管理する。

*   `PROMPT_ASK_PURPOSE`
*   `PROMPT_ASK_MAIN_KEYWORDS`
*   `PROMPT_SUGGEST_SYNONYMS`
*   `PROMPT_SUGGEST_IPC`
*   `PROMPT_CONFIRM_LOGIC`

### 4.3. `core/query_converter.py`: 検索オブジェクトへの変換
対話で完成した`SearchContext`を、PatentsFinderの検索エンジンが理解できる`SearchQuery`オブジェクトに変換する。

```python
from patents_core.core.state import SearchQuery
from .state import SearchContext

def convert_to_search_query(context: SearchContext) -> SearchQuery:
    # contextの各フィールドをSearchQueryのkeyword_groupsやipc_codesにマッピングする
    # 例: main_keywordsとrelated_keyword_groupsを組み合わせてkeyword_groupsを生成
    final_keyword_groups = [context.main_keywords] + context.related_keyword_groups
    
    return SearchQuery(
        ipc_codes=context.ipc_codes,
        keyword_groups=final_keyword_groups,
        # ... 他のフィールドをマッピング
    )
```

### 4.4. `builder.py`: 対話と実行のオーケストレーション
ユーザーとの対話を制御し、最終的にPatentsFinderの検索ワークフローを呼び出す。

```python
# builder.py
from core.state import SearchContext
from core.query_converter import convert_to_search_query
from patents_core.core.state import AppState
from patents_core.core.agent import execute_patent_search_workflow

def run_builder():
    # --- フェーズ1 & 2: 対話によるContext構築 ---
    context = SearchContext()
    # ... (AIとユーザーの対話を通じてcontextを完成させる) ...

    # --- フェーズ3: 検索の実行 ---
    print("\n--- 検索条件を構築し、PatentsFinderの検索を開始します ---")
    search_query = convert_to_search_query(context)
    initial_state = AppState(search_query=search_query, plan_text="対話ビルダーにより生成")
    result_state = execute_patent_search_workflow(initial_state)

    # ... 結果の表示や保存 ...
```

## 5. 開発ステップ

1.  **Step 1: プロジェクトのセットアップと状態定義**
    *   `interactive_builder`配下のファイル群を作成する。
    *   `core/state.py`に`SearchContext`クラスを実装する。

2.  **Step 2: 対話ロジックの実装**
    *   `core/prompts.py`に必要なプロンプトを定義する。
    *   `builder.py`で、`SearchContext`を完成させるための対話ループを実装する。

3.  **Step 3: 変換ロジックの実装**
    *   `core/query_converter.py`に、`SearchContext`から`SearchQuery`への変換ロジックを実装する。

4.  **Step 4: 既存ワークフローとの統合**
    *   `builder.py`の最終ステップとして、`execute_patent_search_workflow`を呼び出す処理を実装する。

5.  **Step 5: 全体テスト**
    *   一連の対話から、PatentsFinderの検索が実行され、結果が出力されるまでの流れを総合的にテストする。

## 6. 将来的な拡張案

*   **GUIの導入:** StreamlitやGradioを用いて、よりリッチなUIで対話できるようにする。
*   **セッションの保存と再開:** 構築途中の検索条件を保存し、後で再開できるようにする。
*   **非特許文献検索への対応:** J-DreamIIIなどの学術文献データベース用の検索式生成にも対応する。

```