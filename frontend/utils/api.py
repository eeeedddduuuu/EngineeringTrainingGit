"""API 调用封装"""
import streamlit as st
import requests

BASE_URL = "http://localhost:8000/api"


def _headers():
    h = {}
    if "token" in st.session_state and st.session_state.token:
        h["Authorization"] = f"Bearer {st.session_state.token}"
    return h


def api_post(path: str, data: dict) -> dict:
    resp = requests.post(f"{BASE_URL}{path}", json=data, headers=_headers())
    if resp.status_code >= 400:
        detail = resp.json().get("detail", "未知错误")
        raise Exception(detail)
    return resp.json()


def api_get(path: str, params: dict | None = None) -> dict:
    resp = requests.get(f"{BASE_URL}{path}", params=params, headers=_headers())
    if resp.status_code >= 400:
        detail = resp.json().get("detail", "未知错误")
        raise Exception(detail)
    return resp.json()
