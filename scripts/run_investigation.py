import os
import sys
from pathlib import Path
import pandas as pd
import time
import argparse
import datetime

# このスクリプト自身の場所を基準にプロジェクトルートを特定
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# 必要なコンポーネントをコアロジックからインポート
from patents_core.core.agent import (
    GENERATE_QUERY_PROMPT, model, run_summary_workflow, 
    generate_sql_and_explanation, execute_search, analyze_results,
    GENERATE_PLAN_PROMPT
)
from patents_core.core.state import AppState, SearchQuery

def run_investigation(user_query: str, limit: int = 10):
    """
    ユーザーのクエリに基づき、特許調査を体系的に実行する。
    結果はタイムスタンプ付きのディレクトリに保存される。
    """
    # 0. 出力用ディレクトリの準備
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "investigations" / f"inv_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"--- Results will be saved to: {output_dir} ---")

    # 1. ユーザーの要求から調査方針を生成
    print("\n--- Generating Search Plan ---")
    plan_chain = GENERATE_PLAN_PROMPT | model
    plan_text = plan_chain.invoke({"chat_history": f"user: {user_query}"}).content
    
    plan_path = output_dir / "plan.txt"
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_text)
    print(f"Plan: {plan_text}")
    print("----------------------------\n")

    # 2. 調査方針から検索クエリを生成
    print("--- Generating Search Query ---")
    query_chain = GENERATE_QUERY_PROMPT | model.with_structured_output(SearchQuery)
    search_query = query_chain.invoke({
        "chat_history": f"user: {user_query}",
        "plan_text": plan_text
    })
    search_query.limit = limit
    # 日付が設定されていない場合はデフォルト値を設定
    if not search_query.publication_date_from:
        search_query.publication_date_from = "20100101"
    if not search_query.publication_date_to:
        search_query.publication_date_to = datetime.datetime.now().strftime("%Y%m%d")

    print(search_query.model_dump_json(indent=2))
    print("-----------------------------\n")

    # 3. 検索と分析を実行
    print("--- Starting Patent Search and Analysis ---")
    initial_state = AppState(search_query=search_query, plan_text=plan_text)
    state_after_sql = generate_sql_and_explanation(initial_state)
    state_after_search = execute_search(state_after_sql)
    state_after_analysis = analyze_results(state_after_search)
    
    analyzed_df = state_after_analysis.analyzed_results
    if analyzed_df is None or analyzed_df.empty:
        print("No patents found.")
        return
        
    print(f"Found and analyzed {len(analyzed_df)} patents.")
    csv_path = output_dir / "patent_search_results.csv"
    analyzed_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"Search results saved to: {csv_path}")
    print("-----------------------------------------\n")

    # 4. 各特許を1件ずつ要約
    print("--- Starting Iterative Summarization ---")
    all_summaries = []
    for index, row in analyzed_df.iterrows():
        print(f"Summarizing patent {index + 1}/{len(analyzed_df)}: {row['publication_number']}...")
        single_patent_df = pd.DataFrame([row])
        summary_state = AppState(
            search_results=single_patent_df,
            selected_patents_for_summary=[row['publication_number']],
            plan_text=plan_text
        )
        try:
            result_state = run_summary_workflow(summary_state)
            summary_text = result_state.summary_result if not result_state.error else f"Error: {result_state.error}"
            all_summaries.append(f"\n\n--- Patent: {row['publication_number']} | Score: {row.get('score', 'N/A'):.4f} ---\n{summary_text}")
            time.sleep(1) # APIレート制限対策
        except Exception as e:
            all_summaries.append(f"\n\n--- Patent: {row['publication_number']} ---\nFatal Error: {e}")
    print("--------------------------------------\n")

    # 5. 全要約を結合して最終レポートを作成
    final_report_content = f"**Investigation Query:** {user_query}\n\n"
    final_report_content += f"**Generated Plan:** {plan_text}\n\n"
    final_report_content += f"**Total Patents Found:** {len(analyzed_df)}\n\n"
    final_report_content += "================================================\n"
    final_report_content += "   Individual Patent Summaries (Sorted by Relevance)\n"
    final_report_content += "================================================\n"
    final_report_content += "".join(all_summaries)

    summary_path = output_dir / "summary_report.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(final_report_content)
    
    print(f"Final summary report saved to: {summary_path}")
    print("Investigation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a patent investigation.")
    parser.add_argument("query", type=str, help="The user's query for the patent investigation.")
    parser.add_argument("--limit", type=int, default=10, help="The maximum number of patents to retrieve.")
    args = parser.parse_args()
    
    run_investigation(args.query, args.limit)
