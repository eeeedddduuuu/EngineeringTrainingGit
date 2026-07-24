"""AI 数字媒体创作助手 - Streamlit 前端入口"""
import streamlit as st

st.set_page_config(page_title="AI 创作助手", page_icon="🎬", layout="wide")

# 简化路由：通过 sidebar 选择页面
st.sidebar.title("🎬 AI 创作助手")

# 登录状态检查
if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.username = None

if st.session_state.token is None:
    st.sidebar.info("请先登录")
    # 加载登录页
    exec(open("pages/login.py", encoding="utf-8").read())
else:
    st.sidebar.success(f"👤 {st.session_state.username}")
    page = st.sidebar.radio(
        "导航",
        ["🏠 创作工作台", "📋 方案浏览", "📜 历史记录", "📊 数据看板"]
    )

    if st.sidebar.button("退出登录"):
        st.session_state.token = None
        st.session_state.username = None
        st.rerun()

    if page == "🏠 创作工作台":
        exec(open("pages/workspace.py", encoding="utf-8").read())
    elif page == "📋 方案浏览":
        exec(open("pages/schemes.py", encoding="utf-8").read())
    elif page == "📜 历史记录":
        exec(open("pages/history.py", encoding="utf-8").read())
    elif page == "📊 数据看板":
        exec(open("pages/dashboard.py", encoding="utf-8").read())
