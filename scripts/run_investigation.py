import os
import sys
from pathlib import Path
import pandas as pd
import time
import argparse
import datetime
import json
import re

# このスクリプト自身の場所を基準にプロジェクトルートを特定
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# 必要なコンポーネントをコアロジックからインポート
from patents_core.core.agent import (
    GENERATE_QUERY_PROMPT, model, run_summary_workflow, 
    generate_sql_and_explanation, execute_search, analyze_results,
    GENERATE_PLAN_PROMPT, PROMPT_CLARIFY_VIEWPOINTS, PROMPT_SELECT_MAIN_KEYWORDS
)
from patents_core.core.state import AppState, SearchQuery
import json
import re
import argparse
import datetime
from pathlib import Path
import sys
import pandas as pd
import time

# このスクリプト自身の場所を基準にプロジェクトルートを特定
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def run_investigation(user_query: str, limit: int = 10, answer: str = None):
    """
    ユーザーのクエリに基づき、特許調査を体系的に実行する。
    結果はタイムスタンプ付きのディレクトリに保存される。
    """
    # 0. 出力用ディレクトリの準備
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = project_root / "investigations" / f"inv_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"--- Results will be saved to: {output_dir} ---")

    # 1. 対話による調査観点の明確化
    print("\n--- Clarifying Investigation Viewpoint ---")
    clarify_chain = PROMPT_CLARIFY_VIEWPOINTS | model
    clarification_question = clarify_chain.invoke({"user_query": user_query}).content
    
    user_response = ""
    if answer:
        user_response = answer
        print("【AIからの質問】")
        print(clarification_question)
        print(f"\n【提供された回答】\n{user_response}")
    else:
        print("\n==================================================")
        print("【AIからの質問】")
        print(clarification_question)
        print("==================================================")
        print("\n上記質問への回答を入力してください（入力後、Enterキーを2回押して入力を完了してください）:")
        user_response_lines = []
        while True:
            line = input()
            if line:
                user_response_lines.append(line)
            else:
                break
        user_response = "\n".join(user_response_lines)

    chat_history = f"user: {user_query}\nassistant: {clarification_question}\nuser: {user_response}"
    print("-----------------------------------------\n")

    # 2. 調査方針を生成
    print("\n--- Generating Search Plan ---")
    plan_chain = GENERATE_PLAN_PROMPT | model
    plan_text = plan_chain.invoke({"chat_history": chat_history}).content
    plan_path = output_dir / "plan.txt"
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(f"Initial Query: {user_query}\n")
        f.write(f"Clarification Response: {user_response}\n\n")
        f.write(f"Generated Plan:\n{plan_text}")
    print(f"Plan: {plan_text}")
    print("----------------------------\n")

    # 3. 検索クエリ（キーワードとIPC）を生成
    print("--- Generating Search Query ---")
    query_chain = GENERATE_QUERY_PROMPT | model.with_structured_output(SearchQuery)
    search_query = query_chain.invoke({"chat_history": chat_history, "plan_text": plan_text})
    
    # 4. メインキーワードの選択と振り分け
    print("\n--- Selecting Main and Related Keywords ---")
    if search_query.keywords:
        select_main_chain = PROMPT_SELECT_MAIN_KEYWORDS | model
        main_keywords_str = select_main_chain.invoke({
            "plan_text": plan_text,
            "keywords": search_query.keywords
        }).content
        
        match = re.search(r'\[.*\]', main_keywords_str, re.DOTALL)
        if match:
            try:
                main_keywords = json.loads(match.group(0))
                search_query.main_keywords = main_keywords
                search_query.related_keywords = [kw for kw in search_query.keywords if kw not in main_keywords]
                print(f"Main Keywords (Subject): {search_query.main_keywords}")
                print(f"Related Keywords (OR): {search_query.related_keywords}")
            except json.JSONDecodeError:
                print("Warning: Failed to parse main keywords. Using all keywords as related.")
                search_query.main_keywords = []
                search_query.related_keywords = search_query.keywords
        else:
            print("Warning: Could not find main keywords list. Using all keywords as related.")
            search_query.main_keywords = []
            search_query.related_keywords = search_query.keywords
    else:
        print("No keywords to process.")
        search_query.main_keywords = []
        search_query.related_keywords = []
    print("-------------------------------------------\n")

    search_query.limit = limit
    if not search_query.publication_date_from:
        search_query.publication_date_from = "20100101"
    if not search_query.publication_date_to:
        search_query.publication_date_to = datetime.datetime.now().strftime("%Y%m%d")

    print("--- Final Search Query Object ---")
    print(search_query.model_dump_json(indent=2))
    print("---------------------------------\n")

    # 5. 検索と分析を実行
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

    # 6. 各特許を1件ずつ要約
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
            time.sleep(1)
        except Exception as e:
            all_summaries.append(f"\n\n--- Patent: {row['publication_number']} ---\nFatal Error: {e}")
    print("--------------------------------------\n")

    # 7. 全要約を結合して最終レポートを作成
    final_report_content = f"**Investigation Query:** {user_query}\n\n"
    final_report_content += f"**Clarification Response:** {user_response}\n\n"
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
    parser.add_argument("--answer", type=str, help="The user's answer to the clarification question.")
    args = parser.parse_args()
    
    run_investigation(args.query, args.limit, args.answer)
