from typing import List

class SearchContext:
    """
    対話を通じて構築される検索条件の状態を管理するクラス。
    """
    def __init__(self):
        self.purpose: str = ""
        self.keyword_groups: List[List[str]] = []
        self.ipc_codes: List[str] = []
        self.date_range_from: str = ""
        self.date_range_to: str = ""
        self.applicants: List[str] = []

    def display(self) -> str:
        """現在の検索条件を整形してユーザーに分かりや��く表示する"""
        display_text = "\n--- 現在の検索条件サマリー ---\n"
        if self.purpose:
            display_text += f"■ 調査目的:\n  - {self.purpose}\n"
        if self.keyword_groups:
            display_text += "■ キーワード (グループ間はAND):\n"
            for i, group in enumerate(self.keyword_groups):
                display_text += f"  - Group {i+1}: ( {' OR '.join(group)} )\n"
        if self.ipc_codes:
            display_text += f"■ 特許分類 (IPC - OR):\n  - {', '.join(self.ipc_codes)}\n"
        
        display_text += "--------------------------------\n"
        return display_text