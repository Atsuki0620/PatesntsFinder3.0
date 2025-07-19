
import argparse
import json
from pathlib import Path
from loguru import logger

# このスクリプトの親ディレクトリをシステムパスに追加
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Gemini APIとの連携は後で実装
# from gemini_api_client import GeminiClient # 仮

logger.remove()
logger.add(
    "logs/suggest_tuning.jsonl",
    format="{message}",
    serialize=True,
    rotation="10 MB",
    compression="zip",
    level="INFO"
)

def load_metrics_report(path: Path) -> dict:
    """メトリクスレポートを読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def suggest_tuning(metrics_report: dict, evaluation_log: List[dict]) -> str:
    """Gemini APIにチューニング案を問い合わせる（仮実装）"""
    logger.info("Requesting tuning suggestions from Gemini API...")
    # ここにGemini API呼び出しロジックを実装
    # 例: GeminiClient().generate_tuning_suggestion(metrics_report, evaluation_log)
    
    # 仮の応答
    suggestion = """
# Suggested changes for config/weights.yaml

similarity_weights:
  title: 0.45
  abstract: 0.35
  claims: 0.20

# Reason: Precision@5 was low. Increased title weight slightly to prioritize direct matches.
"""
    logger.info("Received tuning suggestion from Gemini API.")
    return suggestion

def main(args):
    try:
        project_root = Path(__file__).resolve().parents[1]
        metrics_report_path = project_root / args.metrics_report
        evaluation_log_path = project_root / args.evaluation_log
        
        logger.info(f"Loading metrics report from: {metrics_report_path}")
        metrics_report = load_metrics_report(metrics_report_path)
        
        logger.info(f"Loading evaluation log from: {evaluation_log_path}")
        # evaluation_logはjsonl形式なので、行ごとに読み込む
        evaluation_log = []
        with open(evaluation_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                evaluation_log.append(json.loads(line))
        
        tuning_suggestion = suggest_tuning(metrics_report, evaluation_log)
        
        logger.info("Tuning suggestion generated:")
        logger.info(tuning_suggestion)
        
        # ここで提案をファイルに書き出すなどの処理を追加
        if args.output_suggestion:
            output_path = project_root / args.output_suggestion
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(tuning_suggestion)
            logger.info(f"Tuning suggestion saved to: {output_path}")

    except Exception as e:
        logger.exception("An unexpected error occurred in suggest_tuning.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Suggest tuning parameters based on evaluation results.")
    parser.add_argument(
        "--metrics_report", 
        type=str, 
        default="reports/metrics_report.json",
        help="Path to the metrics report file (json format)."
    )
    parser.add_argument(
        "--evaluation_log", 
        type=str, 
        default="logs/evaluation_log.jsonl",
        help="Path to the detailed evaluation log file (jsonl format)."
    )
    parser.add_argument(
        "--output_suggestion", 
        type=str, 
        help="Optional: Path to save the tuning suggestion."
    )
    args = parser.parse_args()
    main(args)
