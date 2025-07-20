from google.cloud import bigquery
from google.cloud.bigquery import Client, QueryJobConfig, ScalarQueryParameter
import pandas as pd
from patents_core.core.state import SearchQuery
import streamlit as st
from typing import List, Tuple

def build_patent_query(query: SearchQuery, max_results_per_country: int = 3) -> Tuple[str, List[ScalarQueryParameter]]:
    """
    検索条件オブジェクトからBigQueryのSQL文とクエリパラメータを構築する。
    最終FIX版：(IPC OR (キーワードグループAND検索))
    """
    query_params = []
    where_conditions = []
    param_counter = 0

    with_clause = f"""
WITH localized_patents AS (
  SELECT
    p.publication_number,
    SUBSTR(p.publication_number, 1, 2) as country_code,
    (SELECT text FROM UNNEST(p.title_localized)    WHERE language IN ('ja', 'en') ORDER BY (language = 'ja') DESC LIMIT 1) AS title,
    (SELECT text FROM UNNEST(p.abstract_localized) WHERE language IN ('ja', 'en') ORDER BY (language = 'ja') DESC LIMIT 1) AS abstract,
    (SELECT text FROM UNNEST(p.claims_localized)   WHERE language IN ('ja', 'en') ORDER BY (language = 'ja') DESC LIMIT 1) AS claims,
    (SELECT STRING_AGG(name) FROM UNNEST(p.assignee_harmonized)) as assignee_harmonized,
    p.publication_date,
    p.ipc
  FROM `patents-public-data.patents.publications` AS p
),
ranked_patents AS (
  SELECT 
    *,
    ROW_NUMBER() OVER(PARTITION BY country_code ORDER BY publication_date DESC) as rn
  FROM localized_patents
"""

    # --- 日付条件 (必須) ---
    pub_from_str = getattr(query, 'publication_date_from', None) or "20100101"
    pub_to_str = getattr(query, 'publication_date_to', None) or "20250721" # 最新の日付に更新
    where_conditions.append("publication_date BETWEEN @pub_from AND @pub_to")
    query_params.extend([
        ScalarQueryParameter("pub_from", "INT64", int(pub_from_str.replace('-', ''))),
        ScalarQueryParameter("pub_to", "INT64", int(pub_to_str.replace('-', '')))
    ])

    # --- IPCとキーワードの複合条件 ---
    sub_where_parts = []

    # IPC条件 (OR)
    if query.ipc_codes:
        ipc_wheres = []
        for code in query.ipc_codes:
            param_name = f"param_{param_counter}"
            param_counter += 1
            ipc_wheres.append(f"EXISTS (SELECT 1 FROM UNNEST(ipc) c WHERE c.code LIKE @{param_name})")
            query_params.append(ScalarQueryParameter(param_name, "STRING", f"{code}%"))
        if ipc_wheres:
            sub_where_parts.append(f"({' OR '.join(ipc_wheres)})")

    # キーワード条件 (グループ間はAND, グループ内はOR)
    if query.keyword_groups:
        keyword_group_wheres = []
        for group in query.keyword_groups:
            if not group: continue
            keyword_or_wheres = []
            for kw in group:
                param_name = f"param_{param_counter}"
                param_counter += 1
                keyword_or_wheres.append(f"SEARCH(localized_patents, @{param_name})")
                query_params.append(ScalarQueryParameter(param_name, "STRING", kw))
            if keyword_or_wheres:
                keyword_group_wheres.append(f"({' OR '.join(keyword_or_wheres)})")
        if keyword_group_wheres:
            sub_where_parts.append(f"({' AND '.join(keyword_group_wheres)})")

    # IPCとキーワードの条件全体をORで結合
    if sub_where_parts:
        where_conditions.append(f"({' OR '.join(sub_where_parts)})")

    # --- 最終的なSQLの組み立て ---
    final_where_clause = " AND ".join(where_conditions)

    sql = f"""{with_clause}
WHERE {final_where_clause}
)
SELECT
    publication_number,
    title,
    abstract,
    claims,
    assignee_harmonized,
    publication_date,
    (SELECT ARRAY_AGG(c.code) FROM UNNEST(ipc) AS c) AS ipc_codes
FROM ranked_patents
WHERE rn <= {max_results_per_country}
LIMIT @limit
"""
    query_params.append(ScalarQueryParameter("limit", "INT64", query.limit))

    return sql, query_params


def search_patents_in_bigquery(_query: SearchQuery) -> pd.DataFrame:
    """
    build_patent_queryで生成したSQLを使い、BigQueryの公開特許データセットを検索する
    """
    print("--- Executing BigQuery Search ---")
    try:
        client = Client()
    except Exception as e:
        st.error(f"BigQueryクライアントの初期化に失敗しました。GCP認証情報を確認してください。: {e}")
        return pd.DataFrame()

    # SQLとパラメータを生成
    sql, query_params = build_patent_query(_query)

    job_config = QueryJobConfig(query_parameters=query_params)

    print("--- BigQuery実行クエリ ---")
    print(sql)
    print("--- クエリパラメータ ---")
    print([f"name: {p.name}, type: {p.type_}, value: {p.value}" for p in query_params])

    try:
        query_job = client.query(sql, job_config=job_config)
        results_df = query_job.result().to_dataframe()
        print(f"{len(results_df)}件の特許が見つかりました。")
        return results_df
    except Exception as e:
        st.error(f"BigQueryでの検索中にエラーが発生しました: {e}")
        expected_columns = [
            'publication_number', 'title', 'abstract', 'claims',
            'assignee_harmonized', 'publication_date', 'ipc_codes'
        ]
        return pd.DataFrame(columns=expected_columns)
