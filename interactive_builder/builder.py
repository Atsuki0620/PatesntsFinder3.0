import os
import sys
import re
from typing import List

# --- パス設定 ---
# このスクリプトの場所を基準にプロジェクトルートを特定し、パスを追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# --- 必要なコンポーネントをインポート ---
from patents_core.core.state import AppState, SearchQuery
from patents_core.core.agent import execute_patent_search_workflow
from interactive_builder.core.state import SearchContext
from interactive_builder.core.query_converter import convert_to_search_query

# --- 対話ヘルパー関数 ---

def ask_user_for_input(prompt: str, is_list: bool = True) -> List[str]:
    """ユーザーに質問し、カンマ（全角・半角）区切りの入力をリストとして受け取る"""
    print(f"\n🤖 {prompt}")
    user_input = input("👤 > ").strip()
    if not user_input:
        return []
    if is_list:
        # 全角・半角のカンマ、およびスペースで分割する
        return [item.strip() for item in re.split(r'[,
、]+', user_input) if item.strip()]
    # is_list=Falseの場合は、単一要素のリストとして返す
    return [user_input]

# --- メインの対話フロー ---

def run_builder():
    """対話型検索式ビルダーのメインループ（最終FIX版）"""
    context = SearchContext()
    print("ようこそ！対話型PatentsFinder検索条件ビルダーへ。")
    print("調査したい内容を、いくつかのステップに分けて入力してください。")

    # --- フェーズ1: 基本情報の入力 ---
    purpose_input_list = ask_user_for_input("1. 調査目的を簡潔に教えてください (例: 先行技術調査)", is_list=False)
    context.purpose = purpose_input_list[0] if purpose_input_list else "（指定なし）"

    # --- フェーズ2: キーワードグループの入力 ---
    print("\n--- ANDで結合するキーワードグループを順番に入力してください ---")
    group_num = 1
    while True:
        group_input = ask_user_for_input(f"Group {group_num}: (カンマ区切り, なければEnterのみ)")
        if not group_input:
            if group_num == 1:
                print("ℹ️ キーワードが入力されませんでした。")
            break
        context.keyword_groups.append(group_input)
        group_num += 1

    # --- フェーズ3: IPCと件数の入力 ---
    context.ipc_codes = ask_user_for_input("IPCコードを入力してください (カンマ区切り, なければEnterのみ)")
    
    context.display()
    
    limit_input_list = ask_user_for_input("最大何件の特許を取得しますか？ (デフォルト: 10)", is_list=False)
    try:
        limit = int(limit_input_list[0]) if limit_input_list else 10
    except (ValueError, IndexError):
        print("無効な数値です。デフォルトの10件を使用します。")
        limit = 10

    if input(f"\n🤖 この条件で検索を実行しますか？ (y/N): ").strip().lower() != 'y':
        print("\n検索を中止しました。")
        return

    # --- フェーズ4: 検索の実行 ---
    search_query = convert_to_search_query(context)
    search_query.limit = limit
    
    print("\n--- 最終的な検索クエリ ---")
    print(search_query.model_dump_json(indent=2))
    
    initial_state = AppState(search_query=search_query, plan_text=context.purpose)
    
    print("\n--- PatentsFinderの検索・分析ワークフローを開始します ---")
    result_state = execute_patent_search_workflow(initial_state)

    if result_state.error:
        print(f"\n❌ エラーが発生しました: {result_state.error}")
    elif result_state.analyzed_results is not None and not result_state.analyzed_results.empty:
        print(f"\n✅ 検索・分析が完了しました。{len(result_state.analyzed_results)}件の特許が見つかりました。")
        print("--- 結果のプレビュー ---")
        print(result_state.analyzed_results.head())
    else:
        print("\nℹ️ 関連する特許は見つかりませんでした。")

    print("\n対話型検索ビルダーを終了します。")

if __name__ == "__main__":
    run_builder()
