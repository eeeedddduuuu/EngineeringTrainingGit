"""创作工作台页面"""
import streamlit as st
from utils.api import api_post, api_get

st.title("🏠 创作工作台")

with st.form("creation_form"):
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("创作主题 *", placeholder="例如：秋季护肤好物推荐")
        target_audience = st.text_input("目标受众 *", placeholder="例如：25-35岁职场女性")
    with col2:
        platform = st.selectbox("发布平台 *", ["douyin", "xiaohongshu", "bilibili"],
                                format_func=lambda x: {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}[x])
        duration = st.selectbox("视频时长 *", ["30s", "60s", "3min"])
    style = st.text_input("内容风格", placeholder="例如：干货+轻娱乐（选填，默认通用）")
    submitted = st.form_submit_button("🚀 开始创作", use_container_width=True)

if submitted:
    if not topic or not target_audience:
        st.error("请填写必填项（带 * 的字段）")
    else:
        try:
            resp = api_post("/creation/start", {
                "topic": topic,
                "target_audience": target_audience,
                "platform": platform,
                "duration": duration,
                "style": style or "通用"
            })
            task_id = resp["task_id"]
            st.session_state.current_task_id = task_id
            st.success(f"创作任务已提交！（任务ID: {task_id[:8]}...）")
        except Exception as e:
            st.error(f"提交失败：{e}")

# 轮询任务状态
if "current_task_id" in st.session_state:
    task_id = st.session_state.current_task_id
    with st.spinner("AI 正在创作中..."):
        import time
        while True:
            try:
                resp = api_get(f"/task/{task_id}/status")
                status = resp["status"]
                if status == "completed":
                    st.success("创作完成！请前往「方案浏览」查看结果。")
                    del st.session_state.current_task_id
                    break
                elif status == "failed":
                    st.error(f"创作失败：{resp.get('result', {}).get('detail', '未知错误')}")
                    del st.session_state.current_task_id
                    break
                else:
                    st.info(resp.get("progress", "处理中..."))
                    time.sleep(2)
            except Exception as e:
                st.warning(f"轮询异常：{e}（继续等待...）")
                time.sleep(2)
