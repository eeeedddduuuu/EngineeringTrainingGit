"""登录/注册页面"""
import streamlit as st
from utils.api import api_post

st.title("🔐 登录 / 注册")

tab1, tab2 = st.tabs(["登录", "注册"])

with tab1:
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        if st.form_submit_button("登录"):
            if not username or not password:
                st.error("请填写用户名和密码")
            else:
                try:
                    resp = api_post("/auth/login", {"username": username, "password": password})
                    st.session_state.token = resp["access_token"]
                    st.session_state.username = resp["username"]
                    st.success("登录成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"登录失败：{e}")

with tab2:
    with st.form("register_form"):
        new_username = st.text_input("用户名（3-20位字母数字下划线）")
        new_password = st.text_input("密码（至少6位）", type="password")
        new_email = st.text_input("邮箱（选填）")
        if st.form_submit_button("注册"):
            if len(new_username) < 3:
                st.error("用户名至少3位")
            elif len(new_password) < 6:
                st.error("密码至少6位")
            else:
                try:
                    resp = api_post("/auth/register", {
                        "username": new_username,
                        "password": new_password,
                        "email": new_email or None
                    })
                    st.success(resp.get("message", "注册成功！请切换到登录标签"))
                except Exception as e:
                    st.error(f"注册失败：{e}")
