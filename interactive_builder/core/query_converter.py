import sys
import os

# --- パス設定 ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# --- 必要なコンポーネントをインポート ---
from patents_core.core.state import SearchQuery
from interactive_builder.core.state import SearchContext

def convert_to_search_query(context: SearchContext) -> SearchQuery:
    """
    対話で構築されたSearchContextオブジェクトを、
    PatentsFinderの検索エンジンが��解できるSearchQueryオブジェクトに変換する。
    """
    all_keywords = [kw for group in context.keyword_groups for kw in group]

    return SearchQuery(
        ipc_codes=context.ipc_codes,
        keywords=list(set(all_keywords)),
        keyword_groups=context.keyword_groups,
        publication_date_from=context.date_range_from,
        publication_date_to=context.date_range_to,
        assignees=context.applicants
    )
