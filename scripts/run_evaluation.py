

import argparse
import json
import os
import pandas as pd
from pathlib import Path
from typing import List, Dict
from loguru import logger

# このスクリプトの親ディレクトリをシステムパスに追加
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from patents_core.core.agent import execute_patent_search_workflow
from patents_core.core.state import AppState, SearchQuery
from evaluation.metrics import evaluate_with_ragas

# Loguruの設定
logger.remove()
logger.add(
    "logs/evaluation_log.jsonl",
    format="{message}",
    serialize=True,
    rotation="10 MB",
    compression="zip",
    level="INFO"
)

def load_gold_standard(path: Path) -> List[dict]:
    """評価用の正解データを読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def run_single_evaluation(query_item: dict) -> Dict:
    """1つのクエリに対して検索を実行し、RAGAs評価に必要なデータを返す"""
    query_id = query_item['query_id']
    logger.info(f"Running evaluation for query: {query_id}")
    
    # APIキーの存在チェック
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        error_msg = "API keys (OPENAI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS) are not set."
        logger.error(f"  [ERROR] {error_msg}")
        return {"query_id": query_id, "error": error_msg, "results": []}

    try:
        search_query = SearchQuery(**query_item['search_query'])
        app_state = AppState(search_query=search_query, plan_text="This is a dummy plan text for evaluation.")
        
        result_state = execute_patent_search_workflow(app_state)
        
        if result_state.error:
            logger.error(f"  Error from workflow: {result_state.error}")
            return {"query_id": query_id, "error": result_state.error, "results": []}
            
        retrieved_ids = result_state.analyzed_results['publication_number'].tolist()
        
        # コンテキストを上位5件に制限
        contexts = [doc for doc in result_state.analyzed_results['abstract'].tolist()[:5]]

        return {
            "query_id": query_id,
            "question": query_item['question'],
            "answer": result_state.summary_result,
            "contexts": contexts,
            "ground_truths": "\n".join(
                result_state.analyzed_results[result_state.analyzed_results['publication_number'].isin(query_item['expected_ids'])]
                ['abstract'].tolist()
            ) if not result_state.analyzed_results[result_state.analyzed_results['publication_number'].isin(query_item['expected_ids'])].empty
            else ""
        }
    except Exception as e:
        logger.exception(f"  [FATAL] An unexpected exception occurred in workflow execution for {query_id}")
        return {"query_id": query_id, "error": str(e), "results": []}

def main(args):
    """評価プロセス全体を管理する"""
    try:
        project_root = Path(__file__).resolve().parents[1]
        gold_standard_path = project_root / args.gold_standard
        output_report_path = project_root / args.output_report
        
        logger.info(f"Loading gold standard from: {gold_standard_path}")
        gold_standard = load_gold_standard(gold_standard_path)
        
        evaluation_results = [run_single_evaluation(item) for item in gold_standard]
        
        evaluation_results_for_ragas = []
        for result in evaluation_results:
            if result.get("error"):
                logger.warning(f"Skipping RAGAs evaluation for {result.get('query_id', 'unknown_query')} due to error: {result['error']}")
                continue
            evaluation_results_for_ragas.append({
                "question": result['question'],
                "answer": result['answer'],
                "contexts": result['contexts'],
                "ground_truths": result['ground_truths']
            })

        report = {
            "summary_metrics": {},
            "detailed_results": []
        }

        if evaluation_results_for_ragas:
            logger.info("Running RAGAs evaluation...")
            ragas_result = evaluate_with_ragas(evaluation_results_for_ragas)
            
            if ragas_result is None:
                logger.error("RAGAs evaluation failed: evaluate_with_ragas returned None.")
                report["summary_metrics"] = {"error": "RAGAs evaluation failed."}
            else:
                logger.info("RAGas evaluation completed.")
                scores_df = ragas_result.to_pandas()
                report["summary_metrics"] = scores_df.mean(numeric_only=True).to_dict()
                report["detailed_results"] = scores_df.to_dict('records')
        else:
            logger.warning("No valid results to evaluate with RAGAs.")
            report["summary_metrics"] = {"status": "No evaluation performed."}

        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        logger.info(f"\nEvaluation finished. Report saved to: {output_report_path}")
        logger.info(json.dumps(report['summary_metrics'], indent=2))
    except Exception as e:
        logger.exception(f"An unexpected error occurred in main")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run patent search evaluation.")
    parser.add_argument(
        "--gold_standard", 
        type=str, 
        default="evaluation/gold_standard.jsonl",
        help="Path to the gold standard file (jsonl format)."
    )
    parser.add_argument(
        "--output_report", 
        type=str, 
        default="reports/metrics_report.json",
        help="Path to save the evaluation report (json format)."
    )
    args = parser.parse_args()
    main(args)

