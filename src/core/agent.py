from langgraph.graph import StateGraph, END
from typing import Literal
from core.state import AppState, SearchQuery
from core.tools import build_patent_query, search_patents_in_bigquery
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
import os
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- モデル定義 ---
model = ChatOpenAI(temperature=0, model="gpt-4o", api_key=os.environ.get("OPENAI_API_KEY"))
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.environ.get("OPENAI_API_KEY"))

# --- プロンプトテンプレート ---
# ルーター用プロンプト
ROUTER_PROMPT = ChatPromptTemplate.from_template(
    """あなたは、ユーザーとの対話の文脈を読み解き、次に取るべきアクションを判断するルーターです。
    以下の対話履歴から、ユーザーの意図を判断し、'continue_dialogue'（対話継続）か 'generate_query'（検索条件の生成）のどちらかを選択してください。

    対話履歴:
    {chat_history}

    判断基準:
    - ユーザーが最初の質問をしたばかり、または情報が不足している場合は 'continue_dialogue'。
    - 検索対象が具体的になり、キーワードや技術分野が明確になった場合、またはユーザーが「進めて」「検索して」「条件生成」のような明確な指示をした場合は 'generate_query'。

    あなたの判断（'continue_dialogue' または 'generate_query' のみを出力）:"""
)

# 対話継続用プロンプト
CONTINUE_DIALOGUE_PROMPT = ChatPromptTemplate.from_template(
    """あなたは、特許調査をサポートする親切なAIアシスタントです。
    ユーザーとの対話を続け、調査したい内容を具体化する手助けをしてください。
    以下の対話履歴を参考に、ユーザーに質問を投げかけてください。

    対話履歴:
    {chat_history}

    あなたの応答:"""
)

# 条件生成用プロンプト
GENERATE_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "あなたは、ユーザーとの対話履歴から、特許検索のための構造化されたクエリ（IPCコード、キーワード）を生成する専門家です。対話の文脈全体を考慮してください。"),
    ("human", """以下の対話履歴を基に、特許検索クエリをJSON形式で生成してください。

    対話履歴:
    {chat_history}

    あなたのタスク:
    1. 対話履歴から、検索に最も適したキーワードを日本語と英語の両方で抽出する。
    2. 対話履歴から、関連性の高いIPCコードを複数抽出する。""")
])

# SQL解説用プロンプト
PROMPT_EXPLAIN_SQL = ChatPromptTemplate.from_template("以下の特許検索SQLが何をしているのか、技術者でない人にも分かるように簡潔に解説してください。\n\nSQL:\n{sql}")

# 検索条件オブジェクト解説用プロンプト
PROMPT_EXPLAIN_SEARCH_QUERY = ChatPromptTemplate.from_template("以下の特許検索条件オブジェクトが何を示しているのか、技術者でない人にも分かるように簡潔に解説してください。\n\n検索条件オブジェクト:\n{search_query_json}")

# 要約用プロンプト
PROMPT_SUMMARIZE_PATENTS = ChatPromptTemplate.from_template(
    """あなたは、企業の知財部に所属する経験豊富な特許調査の専門家です。
    以下の複数の特許情報について、それぞれの要点をまとめ、全体としてどのような技術動向が読み取れるか解説してください。

    特許リスト:
    {patent_list}

    あなたのタスク:
    1. 各特許の核心技術を1〜2文で要約する。
    2. 全体を俯瞰し、共通する技術的課題や、各社のアプローチの違いなどを解説する。
    """
)

# --- LangGraph ノード定義 ---
def route_action(state: AppState) -> Literal["continue_dialogue", "generate_query"]:
    print("--- Node: route_action ---")
    latest_user_input = state.chat_history[-1][1] if state.chat_history else ""
    if any(keyword in latest_user_input for keyword in ["進めて", "検索して", "条件生成", "これでいい", "OK"]):
        return "generate_query"
    chain = ROUTER_PROMPT | model
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    response = chain.invoke({"chat_history": history_str}).content
    return "generate_query" if 'generate_query' in response else "continue_dialogue"

def continue_dialogue(state: AppState) -> AppState:
    print("--- Node: continue_dialogue ---")
    chain = CONTINUE_DIALOGUE_PROMPT | model
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    response = chain.invoke({"chat_history": history_str}).content
    response += "\n\n現在の情報で検索条件を生成したい場合は、『進めて』と入力してください。"
    state.chat_history.append(("assistant", response))
    return state

def generate_query(state: AppState) -> AppState:
    print("--- Node: generate_query ---")
    chain = GENERATE_QUERY_PROMPT | model.with_structured_output(SearchQuery)
    history_str = "\n".join([f"{role}: {msg}" for role, msg in state.chat_history])
    state.search_query = chain.invoke({"chat_history": history_str})
    state.chat_history.append(("assistant", "対話の内容に基づいて、検索条件を生成しました。右のエリアで内容を確認・編集してください。よろしければ『検索開始』ボタンを押してください。"))
    return state

def generate_sql_and_explanation(state: AppState) -> AppState:
    """検索クエリからSQL文と解説を生成する"""
    print("--- Node: generate_sql_and_explanation ---")
    state.current_agent_node = "generate_sql_and_explanation"

    # 統一されたビルダー関数を使い、SQLとパラメータを生成
    sql, _ = build_patent_query(state.search_query)
    state.generated_sql = sql

    # 生成されたSQLをユーザー向けに解説
    chain_sql_explain = PROMPT_EXPLAIN_SQL | model
    state.sql_explanation = chain_sql_explain.invoke({"sql": sql}).content

    # 検索条件オブジェクトをユーザー向けに解説
    chain_query_explain = PROMPT_EXPLAIN_SEARCH_QUERY | model
    state.search_query_explanation = chain_query_explain.invoke({"search_query_json": state.search_query.model_dump_json(indent=2)}).content
    
    return state

def execute_search(state: AppState) -> AppState:
    print("--- Node: execute_search ---")
    state.current_agent_node = "execute_search"
    try:
        df = search_patents_in_bigquery(state.search_query)
        state.search_results = df
    except Exception as e:
        state.error = f"検索中にエラーが発生しました: {e}"
    return state

def analyze_results(state: AppState) -> AppState:
    """検索結果を分析し、類似度を計算する"""
    print("--- Node: analyze_results ---")
    state.current_agent_node = "analyze_results"
    
    df = state.search_results
    if df is None or df.empty:
        print("分析対象の検索結果がないため、スキップします。")
        state.analyzed_results = pd.DataFrame()
        return state

    tech_content = "\n".join([msg for role, msg in state.chat_history if role == "user"]) or "特許検索"

    # リファクタリング後のクエリから返される統一カラム名を使用
    required_cols = ['title', 'abstract', 'claims']
    for col in required_cols:
        if col not in df.columns:
            state.error = f"検索結果に必須カラム({col})がありません。SQLクエリを確認してください。"
            state.analyzed_results = pd.DataFrame()
            return state

    patents_text = (
        "Title: " + df["title"].fillna("") + "\n" +
        "Abstract: " + df["abstract"].fillna("") + "\n" +
        "Claims: " + df["claims"].fillna("")
    ).tolist()

    try:
        tech_content_embedding = embeddings_model.embed_query(tech_content)
        patents_embeddings = embeddings_model.embed_documents(patents_text)
        similarities = cosine_similarity([tech_content_embedding], patents_embeddings)[0]
        
        analyzed_df = df.copy()
        analyzed_df["similarity"] = similarities
        state.analyzed_results = analyzed_df.sort_values(by="similarity", ascending=False).reset_index(drop=True)
    except Exception as e:
        state.error = f"埋め込みベクトルの計算中にエラーが発生しました: {e}"
        state.analyzed_results = df # ソート前の結果を返す
        
    print("分析が完了しました。")
    return state

def summarize_selected_patents(state: AppState) -> AppState:
    print("--- Node: summarize_selected_patents ---")
    state.current_agent_node = "summarize_selected_patents"
    
    if state.search_results is None or not state.selected_patents_for_summary:
        state.summary_result = "要約対象の特許が選択されていません。"
        return state

    selected_df = state.search_results[state.search_results['publication_number'].isin(state.selected_patents_for_summary)]
    
    if selected_df.empty:
        state.summary_result = "選択された特許が見つかりません。"
        return state

    patent_list_str = selected_df.to_string(index=False)
    chain = PROMPT_SUMMARIZE_PATENTS | model
    state.summary_result = chain.invoke({"patent_list": patent_list_str}).content
    return state

# --- ワークフローの構築 ---
interaction_workflow = StateGraph(AppState)
interaction_workflow.add_node("continue_dialogue", continue_dialogue)
interaction_workflow.add_node("generate_query", generate_query)
interaction_workflow.set_conditional_entry_point(route_action, {"continue_dialogue": "continue_dialogue", "generate_query": "generate_query"})
interaction_workflow.add_edge("continue_dialogue", END)
interaction_workflow.add_edge("generate_query", END)
interaction_app = interaction_workflow.compile()

search_execution_workflow = StateGraph(AppState)
search_execution_workflow.add_node("generate_sql_and_explanation", generate_sql_and_explanation)
search_execution_workflow.add_node("execute_search", execute_search)
search_execution_workflow.add_node("analyze_results", analyze_results)
search_execution_workflow.set_entry_point("generate_sql_and_explanation")
search_execution_workflow.add_edge("generate_sql_and_explanation", "execute_search")
search_execution_workflow.add_edge("execute_search", "analyze_results")
search_execution_workflow.add_edge("analyze_results", END)
search_execution_app = search_execution_workflow.compile()

synopsis_workflow = StateGraph(AppState)
synopsis_workflow.add_node("summarize_selected_patents", summarize_selected_patents)
synopsis_workflow.set_entry_point("summarize_selected_patents")
synopsis_workflow.add_edge("summarize_selected_patents", END)
synopsis_app = synopsis_workflow.compile()

# --- 外部から呼び出す関数 ---
def run_interaction(state: AppState) -> AppState:
    return AppState(**interaction_app.invoke(state))

def execute_patent_search_workflow(state: AppState) -> AppState:
    state.agent_node_graph = search_execution_app.get_graph().draw_mermaid()
    result_dict = search_execution_app.invoke(state)
    return AppState(**result_dict)

def run_summary_workflow(state: AppState) -> AppState:
    result_dict = synopsis_app.invoke(state)
    return AppState(**result_dict)
