from ragas import evaluate
from ragas.metrics import (answer_relevancy, faithfulness, answer_similarity)
from datasets import Dataset
from typing import List, Dict, Optional
from ragas.evaluation import EvaluationResult
from loguru import logger

def evaluate_with_ragas(data: List[Dict]) -> Optional[EvaluationResult]:
    """
    RAGAsライブラリを使用して評価指標を計算する。

    Args:
        data: 評価に必要なデータを含む辞書のリスト。
              各辞書は 'question', 'answer', 'contexts', 'ground_truths' を含む。

    Returns:
        計算された評価指標の辞書。
    """
    # Datasetオブジェクトに変換
    ds = Dataset.from_list(data).rename_columns({"ground_truths": "reference"})

    # 評価メトリクスを定義
    metrics = [
        faithfulness,
        answer_relevancy,
    ]

    # 評価を実行
    try:
        logger.info("Starting RAGAs evaluation within metrics.py...")
        logger.debug(f"Dataset features: {ds.features}")
        logger.debug(f"Dataset head: {ds.to_pandas().head().to_dict()}")
        result = evaluate(ds, metrics)
        logger.info("RAGAs evaluation completed successfully within metrics.py.")
    except Exception as e:
        logger.exception(f"Error during RAGAs evaluation in metrics.py: {e}")
        return None

    return result