import os
import sys
from pathlib import Path
import json
import yaml
import argparse
from langchain_openai import ChatOpenAI

# このスクリプト自身の場所を基準にプロジェクトルートを特定
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def suggest_new_weights(report_path: Path, current_weights_path: Path, output_path: Path):
    """
    評価レポートと現在の重みを基に、OpenAI APIに新しい重みを提案させる。
    """
    # 1. 評価レポートと現在の重みを読み込む
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    with open(current_weights_path, 'r', encoding='utf-8') as f:
        current_weights = yaml.safe_load(f)

    # 2. OpenAI APIに投げるプロンプトを作成
    prompt = f"""あなたは、特許検索システムの性能を最適化するAIアシスタントです。
以下の評価レポートと現在の重み設定を分析し、`answer_relevancy`スコアを最大化するた���の新しい重み設定を提案してください。

**制約条件:**
- `title`, `abstract`, `claims` の3つのキーに対する重みを提案してください。
- 3つの重みの合計は必ず `1.0` にしてください。
- `faithfulness` スコアが `0.95` 未満にならないように、過度な調整は避けてください。
- 出力はYAML形式のキーと値のみとし、他のテキストは含めないでください。

**評価レポート:**
```json
{json.dumps(report, indent=2, ensure_ascii=False)}
```

**現在の重み設定:**
```yaml
{yaml.dump(current_weights, allow_unicode=True)}
```

**新しい重み設定案 (YAML形式):**
"""

    # 3. OpenAI APIを呼び出す
    print("--- Asking OpenAI for new weight suggestions... ---")
    try:
        # APIキーは環境変数 `OPENAI_API_KEY` から自動で読み込まれる
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        response = llm.invoke(prompt)
        suggested_weights_str = response.content
        print("--- OpenAI's Suggestion ---")
        print(suggested_weights_str)
        print("---------------------------")

        # 4. 結果をパースしてファイルに保存
        suggested_weights = yaml.safe_load(suggested_weights_str)
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(suggested_weights, f, allow_unicode=True)
        
        print(f"Successfully saved suggested weights to: {output_path}")

    except Exception as e:
        print(f"An error occurred while calling OpenAI API: {e}")
        print("Creating a dummy suggestion file instead.")
        # エラーが発生した場合はダミーファイルを作成
        dummy_weights = {"similarity_weights": {"title": 0.5, "abstract": 0.4, "claims": 0.1}}
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(dummy_weights, f, allow_unicode=True)
        print(f"Saved dummy weights to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Suggest new weights based on evaluation results.")
    parser.add_argument("--report", type=str, default="reports/metrics_report.json")
    parser.add_argument("--current_weights", type=str, default="config/weights.yaml")
    parser.add_argument("--output", type=str, default="suggested_weights.yaml")
    args = parser.parse_args()

    suggest_new_weights(
        project_root / args.report,
        project_root / args.current_weights,
        project_root / args.output
    )
