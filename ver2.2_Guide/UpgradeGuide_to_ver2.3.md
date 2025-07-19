# GEMINI 開発アプローチ改善方針

## 1. 目的
特許検索アプリにおける **検索精度の継続的改善** と **バグ検出速度の最大化** を両立させるため、ロジック層と UI 層を分離し、Gemini CLI を用いた自律 PDCA サイクルを組み込む。

---

## 2. 3 レイヤ構造

| レイヤ | 役割 | 実装 | 主テスト |
|-------|------|------|---------|
| **Core** | 検索・類似度計算ロジック | `patents_core/` (純 Python) | ユニット + ランク精度 |
| **Evaluation** | PDCA (設定→検索→評価→レポート) | `scripts/pdca_runner.py` | 回帰 + 閾値テスト |
| **UI** | 結果可視化のみ | `app.py` (Streamlit) | 最小限 E2E |

---

## 3. PDCA パイプライン

1. **Plan** – 調査方針自動生成 (5 案) → 選択  
2. **Do** – Core に検索実行、スコア付き DF 取得  
3. **Check** – ゴールドセットと比較し Precision@k / nDCG@k 評価  
4. **Act** – 閾値未満なら Gemini CLI で重み調整提案 → `weights.yaml` 更新 → 再テスト  

```bash
gemini run suggest_tuning   --log logs/latest.log   --metrics reports/metrics.json
```

---

## 4. ロギング & エラーハンドリング

* **loguru** で JSON ログ (`logs/*.jsonl`)。主要キー: `query_id`, `score`, `elapsed_ms` 等  
* 例外ポリシ:

| 層 | 捕捉例外 | アクション |
|----|----------|-----------|
| Core | ネットワーク / Embedding 失敗 | リトライ→ `SearchFailedError` |
| Eval | 指標計算失敗 | 警告ログ |
| UI | 未捕捉例外 | `st.error` + ログ ID 表示 |

---

## 5. テストピラミッド

| レベル | 対象 | ツール | トリガ |
|--------|------|-------|--------|
| ユニット | 関数 | pytest | push |
| ランク精度 | 検索結果 | pytest+pandas | push & nightly |
| 統合 | CLI | pytest+subprocess | push |
| E2E | Streamlit | Playwright | nightly |

---

## 6. 重み・閾値の外部化

* `weights.yaml` に全パラメータを集約  
* テスト失敗時に Bot が **自動 PR** で調整案を提示

---

## 7. 開発フロー

1. Notebook で仮説検証  
2. `.py` テストスクリプト化  
3. Gemini CLI で自動レビュー  
4. PR → CI 通過でマージ  
5. Streamlit 確認のみ

---

## 8. 今後の拡張

* RAGAs 指標を Check フェーズへ
* HyDE / 再ランキング A/B テスト基盤
* ログを Athena/BigQuery で分析し検索履歴可視化
