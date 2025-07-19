import os
import sys
from pathlib import Path
import yaml
import argparse

# このスクリプト自身の場所を基準にプロジェクトルートを特定
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def apply_new_weights(suggestion_path: Path, target_path: Path):
    """
    提案された重みを設定ファイルに適用する。
    """
    try:
        # 1. 提案された重みを読み込む
        with open(suggestion_path, 'r', encoding='utf-8') as f:
            suggested_weights = yaml.safe_load(f)
        
        # 2. ターゲットファイルに書き込む
        with open(target_path, 'w', encoding='utf-8') as f:
            yaml.dump(suggested_weights, f, allow_unicode=True)
            
        print(f"Successfully applied new weights to: {target_path}")
        print("New weights:")
        print(yaml.dump(suggested_weights, allow_unicode=True))

    except FileNotFoundError:
        print(f"Error: Suggestion file not found at {suggestion_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply new suggested weights.")
    parser.add_argument("--suggestion", type=str, default="suggested_weights.yaml")
    parser.add_argument("--target", type=str, default="config/weights.yaml")
    args = parser.parse_args()

    apply_new_weights(
        project_root / args.suggestion,
        project_root / args.target
    )