
import argparse
import yaml
from pathlib import Path
from loguru import logger

logger.remove()
logger.add(
    "logs/apply_tuning.log",
    format="{time} {level} {message}",
    rotation="10 MB",
    compression="zip",
    level="INFO"
)

def apply_tuning_suggestion(suggestion_path: Path, weights_path: Path):
    """チューニング提案をweights.yamlに適用する"""
    logger.info(f"Loading tuning suggestion from: {suggestion_path}")
    with open(suggestion_path, 'r', encoding='utf-8') as f:
        suggestion_content = f.read()
    
    # 提案内容からYAML部分を抽出
    # 仮実装では、提案全体がYAML形式であると仮定
    try:
        suggested_config = yaml.safe_load(suggestion_content)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse tuning suggestion as YAML: {e}")
        return

    logger.info(f"Loading current weights from: {weights_path}")
    with open(weights_path, 'r', encoding='utf-8') as f:
        current_config = yaml.safe_load(f)

    # 提案された変更を現在の設定にマージ
    # ここではsimilarity_weightsのみを対象とする
    if "similarity_weights" in suggested_config:
        current_config["similarity_weights"] = suggested_config["similarity_weights"]
        logger.info("Applied similarity_weights from suggestion.")
    else:
        logger.warning("No 'similarity_weights' found in the suggestion. No changes applied.")

    logger.info(f"Saving updated weights to: {weights_path}")
    with open(weights_path, 'w', encoding='utf-8') as f:
        yaml.dump(current_config, f, indent=2, allow_unicode=True)
    logger.info("Weights updated successfully.")

def main(args):
    try:
        project_root = Path(__file__).resolve().parents[1]
        suggestion_path = project_root / args.suggestion_file
        weights_path = project_root / "config" / "weights.yaml"
        
        apply_tuning_suggestion(suggestion_path, weights_path)

    except Exception as e:
        logger.exception("An unexpected error occurred in apply_tuning.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply tuning suggestions to weights.yaml.")
    parser.add_argument(
        "--suggestion_file", 
        type=str, 
        required=True,
        help="Path to the file containing the tuning suggestion (e.g., output from suggest_tuning.py)."
    )
    args = parser.parse_args()
    main(args)
