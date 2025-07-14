import os
import json
import streamlit as st
from dotenv import load_dotenv

def load_env():
    """環境変数を.envファイルから読み込む"""
    load_dotenv()

def get_openai_api_key() -> str:
    """環境変数からOpenAI APIキーを取得する"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI APIキーが設定されていません。.envファイルまたは環境変数で設定してください。")
        st.stop()
    return api_key

def get_gcp_credentials_info() -> dict:
    """環境変数からGCP認証情報を取得し、内容を辞書として返す"""
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        st.error("GCPの認証情報(GOOGLE_APPLICATION_CREDENTIALS)が設定されていません。.envファイルまたは環境変数で設定してください。")
        st.stop()
    try:
        # If the credential is a JSON string
        if credentials_path.strip().startswith('{'):
            return json.loads(credentials_path)
        # If the credential is a file path
        else:
            with open(credentials_path, 'r') as f:
                return json.load(f)
    except FileNotFoundError:
        st.error(f"GCP認証ファイルが見つかりません: {credentials_path}")
        st.stop()
    except json.JSONDecodeError:
        st.error(f"GCP認証ファイルのJSON形式が正しくありません: {credentials_path}")
        st.stop()
    except Exception as e:
        st.error(f"GCP認証情報の読み込み中にエラーが発生しました: {e}")
        st.stop()
        return {} # st.stop() will exit, but return for completeness
