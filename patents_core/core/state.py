from typing import List, Optional
from pydantic import BaseModel, Field

class SearchQuery(BaseModel):
    """特許検索の検索条件を定義するモデル"""
    ipc_codes: Optional[List[str]] = Field(default=None, description="IPCコードのリスト")
    keywords: Optional[List[str]] = Field(default=None, description="検索キーワードの全リスト")
    keyword_groups: Optional[List[List[str]]] = Field(default=None, description="グループ化された検索キーワードのリスト（AND/OR検索用）")
    publication_date_from: Optional[str] = Field(default=None, description="公開日の開始日 (YYYYMMDD)")
    publication_date_to: Optional[str] = Field(default=None, description="公開日の終了日 (YYYYMMDD)")
    country_codes: Optional[List[str]] = Field(default=None, description="国コードのリスト")
    assignees: Optional[List[str]] = Field(default=None, description="出願人のリスト")
    limit: int = Field(default=100, description="最大取得件数")

class AppState(BaseModel):
    """アプリケーション全体のセッション状態を管理するモデル"""
    chat_history: List[Tuple[str, str]] = Field(default_factory=list, description="ユーザーとAIの対話履歴")
    plan_text: Optional[str] = Field(default=None, description="AIが生成した調査方針")
    search_query: Optional[SearchQuery] = Field(default=None, description="構築された検索クエリ")
    search_query_explanation: Optional[str] = Field(default=None, description="検索クエリの自然言語による解説")
    generated_sql: Optional[str] = Field(default=None, description="生成されたBigQueryのSQL文")
    sql_explanation: Optional[str] = Field(default=None, description="SQL文の自然言語による解説")
    search_results: Optional[pd.DataFrame] = Field(default=None, description="BigQueryからの検索結果")
    analyzed_results: Optional[pd.DataFrame] = Field(default=None, description="類似度計算などで分析された検索結果")
    selected_patents_for_summary: List[str] = Field(default_factory=list, description="ユーザーが要約対象として選択した特許の公開番号リスト")
    summary_result: Optional[str] = Field(default=None, description="選択された特許の要約結果")
    error: Optional[str] = Field(default=None, description="処理中に発生したエラーメッセージ")
    
    # LangGraphの可視化用
    current_agent_node: Optional[str] = Field(default=None, description="現在実行中のエージェントノード名")
    agent_node_graph: Optional[str] = Field(default=None, description="Mermaid形式のエージェントグラフ")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            pd.DataFrame: lambda v: v.to_json(orient='split'),
        }
