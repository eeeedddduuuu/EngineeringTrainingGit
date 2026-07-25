import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
from io import BytesIO
from streamlit.components.v1 import html

# ====================== 全局页面基础配置 ======================
st.set_page_config(
    page_title="AI 数字媒体创作助手 | 实训项目",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 顶配高级CSS美化（紫堇渐变主题，全页面动效） ======================
st.markdown("""
<style>
/* 全局基础 */
* {
    font-family: 'Inter', 'Microsoft YaHei', sans-serif;
}
.stApp {
    background: linear-gradient(180deg, #f7f9ff 0%, #f5f7fb 100%);
}
/* 顶部渐变装饰条 */
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 5px;
    background: linear-gradient(90deg, #6d28d9, #8b5cf6, #a78bfa, #7c3aed);
    z-index: 999999;
    box-shadow: 0 2px 14px rgba(124,58,237,0.35);
}
/* 压缩标题下方的多余间距 */
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
/* 强制移除顶部所有多余空间 */
.stApp > div:first-child {
    padding-top: 0 !important;
}
/* 调整主内容区顶部边距 */
.stMarkdown {
    margin-bottom: 0 !important;
}
/* 移除 sub-header 下方多余间距 */
.sub-header {
    margin-bottom: 12px !important;
}

/* 主标题样式 */
.main-header {
    font-size: 44px;
    font-weight: 800;
    color: #1e293b;
    text-align: center;
    padding: 32px 0 8px;
    letter-spacing: 1.2px;
    background: linear-gradient(90deg, #6d28d9, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.sub-header {
    text-align: center;
    color: #64748b;
    font-size: 16px;
    letter-spacing: 4px;
    margin-bottom: 36px;
}
/* 通用卡片容器 带悬浮动画 */
.primary-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 30px 36px;
    margin-bottom: 28px;
    box-shadow: 0 3px 16px rgba(0,0,0,0.05);
    border: 1px solid #eef2ff;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.primary-card:hover {
    box-shadow: 0 8px 28px rgba(124,58,237,0.12);
    transform: translateY(-2px);
}
.card-title {
    color: #1e293b;
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}
/* 输入控件美化 */
.stTextInput input, .stTextArea textarea, .stSelectbox select, .stFileUploader {
    background: #fff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    font-size: 15px !important;
    transition: all 0.25s ease !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 0 4px rgba(139,92,246,0.1) !important;
    outline: none;
}
/* 主按钮紫色渐变 */
.stButton button {
    background: linear-gradient(135deg, #7c3aed, #8b5cf6) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 32px !important;
    font-size: 15px !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 12px rgba(124,58,237,0.22) !important;
}
.stButton button:hover {
    background: linear-gradient(135deg, #6d28d9, #7c3aed) !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(124,58,237,0.28) !important;
}
.stButton button:active {
    transform: translateY(0);
}
/* 侧边栏样式重写 */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #eef2ff !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    color: #475569 !important;
    box-shadow: none !important;
    text-align: left !important;
    padding: 12px 18px !important;
    border-radius: 12px !important;
    font-weight: 500 !important;
    margin: 4px 0;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: #f3f0ff !important;
    color: #7c3aed !important;
}
/* 方案卡片（3列展示） */
.scheme-wrap {
    background: #f8faff;
    border-radius: 18px;
    padding: 24px;
    border: 1px solid #eef2ff;
    height: 100%;
    transition: all 0.3s ease;
}
.scheme-wrap:hover {
    border-color: #c4b5fd;
    box-shadow: 0 4px 16px rgba(124,58,237,0.08);
}
.version-badge {
    display: inline-block;
    padding: 4px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    background: #ede9fe;
    color: #6d28d9;
    margin-bottom: 12px;
}
.scheme-name {
    font-size: 18px;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 8px;
}
.scheme-desc {
    color: #475569;
    font-size: 14px;
    line-height: 1.75;
}
.platform-tag {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    background: #f3f0ff;
    color: #7c3aed;
    margin-right: 6px;
    margin-top: 10px;
}
/* 推荐高亮框 */
.recommend-panel {
    background: linear-gradient(90deg, #f3f0ff, #f8faff);
    border-left: 4px solid #8b5cf6;
    padding: 16px 20px;
    border-radius: 0 14px 14px 0;
    margin-top: 16px;
}
.rec-title {
    font-size: 13px;
    font-weight: 700;
    color: #7c3aed;
    letter-spacing: 1px;
}
.rec-text {
    font-size: 14px;
    color: #334155;
    margin-top: 4px;
    line-height: 1.7;
}
/* 空状态页面 */
.empty-container {
    text-align: center;
    padding: 80px 20px;
    color: #94a3b8;
    font-size: 16px;
}
/* 提示信息框 */
.info-tip {
    background: #f3f0ff;
    border-radius: 16px;
    padding: 22px;
    border: 1px solid #e0d8f5;
    color: #4c1d95;
    line-height: 1.8;
}
/* 进度条美化 */
div[data-testid="stProgress"] > div {
    background: linear-gradient(90deg, #7c3aed, #a78bfa) !important;
    border-radius: 999px !important;
}
/* 滚动条美化 */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #f1f5f9;
}
::-webkit-scrollbar-thumb {
    background: #c4b5fd;
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: #8b5cf6;
}
</style>
""", unsafe_allow_html=True)

# ====================== 全局常量 & Session状态初始化 ======================
API_BASE = "http://127.0.0.1:8000/api"

def init_session():
    """初始化全局会话缓存"""
    default_state = {
        "token": None,
        "user": None,
        "current_page": "📝 工作台",
        "task_id": None,
        "task_progress": 0,
        "task_running": False,
        "schemes_list": [],
        "history_records": [],
        "sample_stats": pd.DataFrame({
            "平台": ["抖音","小红书","B站","抖音","小红书","B站","抖音"],
            "主题": ["护肤","美食","数码","旅行","测评","剧情","好物"],
            "数量": [28,36,22,18,24,16,30]
        })
    }
    for key, val in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ====================== 工具函数：统一请求封装（带JWT鉴权） ======================
def api_request(path, method="GET", json_data=None, files=None):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    full_url = f"{API_BASE}{path}"
    try:
        if method == "GET":
            res = requests.get(full_url, headers=headers, timeout=15)
        elif method == "POST":
            if files:
                res = requests.post(full_url, headers=headers, json=json_data, files=files, timeout=15)
            else:
                res = requests.post(full_url, headers=headers, json=json_data, timeout=15)
        elif method == "PUT":
            res = requests.put(full_url, headers=headers, json=json_data, timeout=15)
        return res
    except Exception as e:
        st.error(f"接口请求失败：{str(e)}，请检查后端服务是否启动")
        return None

# ====================== 页面1：登录/注册页面（全屏居中卡片） ======================
def render_login_page():
    st.markdown('<div class="main-header">🎬 AI 数字媒体创作助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">MULTIMEDIA AI CREATOR | AI数字媒体创作平台</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="text-align: center; margin: 16px 0 28px 0;">
    <p style="color: #64748b; font-size: 14px; letter-spacing: 1px; line-height: 1.8;">
        <span style="background: #f3f0ff; padding: 4px 14px; border-radius: 20px; color: #6d28d9; font-weight: 500; margin: 0 4px;">🎮 游戏</span>
        <span style="background: #f3f0ff; padding: 4px 14px; border-radius: 20px; color: #6d28d9; font-weight: 500; margin: 0 4px;">🎬 短视频</span>
        <span style="background: #f3f0ff; padding: 4px 14px; border-radius: 20px; color: #6d28d9; font-weight: 500; margin: 0 4px;">📱 社交媒体</span>
        <span style="background: #f3f0ff; padding: 4px 14px; border-radius: 20px; color: #6d28d9; font-weight: 500; margin: 0 4px;">📺 品牌宣发</span>
    </p>
    <p style="color: #94a3b8; font-size: 13px; margin-top: 8px;">AI 驱动 · 一键生成 · 多平台适配</p>
</div>
""", unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([1, 2.4, 1])
    with col_center:
        st.markdown('<div class="primary-card">', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["🔐 用户登录", "📝 新用户注册"])
        
        # 登录表单
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                uname = st.text_input("用户名", placeholder="输入你的账号")
                pwd = st.text_input("登录密码", type="password", placeholder="输入密码")
                submit_login = st.form_submit_button("立即登录", use_container_width=True)
                if submit_login:
                    if not uname or not pwd:
                        st.warning("请填写完整账号密码！")
                    else:
                        resp = api_request("/auth/login", "POST", {"username": uname, "password": pwd})
                        if resp and resp.status_code == 200:
                            data = resp.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user = {"username": data["username"]}
                            st.success("🎉 登录成功，正在跳转工作台...")
                            time.sleep(1.2)
                            st.rerun()
                        elif resp:
                            st.error(resp.json().get("detail", "账号或密码错误"))
        
        # 注册表单
        with tab_register:
            with st.form("reg_form"):
                reg_user = st.text_input("设置用户名", placeholder="自定义账号")
                reg_pwd = st.text_input("设置密码", type="password", placeholder="6位以上字符")
                reg_pwd2 = st.text_input("确认密码", type="password", placeholder="再次输入密码")
                submit_reg = st.form_submit_button("完成注册", use_container_width=True)
                if submit_reg:
                    if not reg_user or not reg_pwd:
                        st.warning("账号密码不能为空！")
                    elif reg_pwd != reg_pwd2:
                        st.error("两次输入密码不一致，请重新填写")
                    else:
                        resp = api_request("/auth/register", "POST", {"username": reg_user, "password": reg_pwd})
                        if resp and resp.status_code == 200:
                            st.success("✅ 注册完成！切换登录标签页登录系统")
                        elif resp:
                            st.error(resp.json().get("detail", "注册失败，用户名已存在"))
        st.markdown('</div>', unsafe_allow_html=True)

# ====================== 侧边栏导航（带用户信息+页面切换） ======================
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎬 AI创作助手")
        st.divider()
        if st.session_state.user:
            if isinstance(st.session_state.user, dict):
                st.markdown(f"👤 当前用户：**{st.session_state.user.get('username', '未知')}**")
            else:
                st.markdown(f"👤 当前用户：**{st.session_state.user}**")
        st.divider()
        page_list = [
            "📝 工作台",
            "📋 历史记录",
            "📊 数据看板"
        ]
        for page in page_list:
            btn = st.button(page, use_container_width=True, key=f"nav_{page}")
            if btn:
                st.session_state.current_page = page
                st.rerun()
        st.divider()
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.schemes_list = []
            st.session_state.task_running = False
            st.rerun()

# ====================== 页面2：创作工作台（核心业务页） ======================
def render_workbench():
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🚀 智能创作工作台</div>', unsafe_allow_html=True)
    col_input, col_tips = st.columns([3, 1])
    with col_input:
        with st.form("create_form"):
            topic = st.text_input("创作主题 *", placeholder="例：秋季平价护肤攻略、二次元游戏剧情脚本")
            audience = st.text_input("目标受众", placeholder="例：20-30岁学生、数码发烧友、宝妈群体")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                platform = st.selectbox("发布平台", ["抖音", "小红书", "B站"])
            with col_b:
                duration = st.selectbox("视频时长", ["15秒", "30秒", "60秒"])
            with col_c:
                style = st.selectbox("内容风格", ["干货科普", "轻娱乐", "情感走心", "剧情故事", "测评种草"])
            upload_file = st.file_uploader("上传参考素材（图片/音频）", accept_multiple_files=True)
            submit_gen = st.form_submit_button("✨ 一键启动AI创作", use_container_width=True)
            
            if submit_gen:
                if not topic:
                    st.error("创作主题为必填项，请完善！")
                else:
                    import requests
                    platform_map = {
                        "抖音": "douyin",
                        "小红书": "xiaohongshu",
                        "B站": "bilibili"
                    }
                    duration_map = {
                        "15秒": "15s",
                        "30秒": "30s",
                        "60秒": "60s"
                    }
                    payload = {
                        "topic": topic,
                        "target_audience": audience,
                        "platform": platform_map.get(platform, "douyin"),
                        "duration": duration_map.get(duration, "30s"),
                        "style": style
                    }
                    try:
                        resp = requests.post(
                            "http://127.0.0.1:8000/api/creation/start",
                            json=payload,
                            headers={"Authorization": f"Bearer {st.session_state.token}"}
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.success(f"✅ 任务已提交，任务ID：{data.get('task_id', '未知')}")
                            mock_scheme = [
                                {
                                    "version": "A",
                                    "title": f"{topic}｜简洁干货版",
                                    "description": "开篇直击痛点，结构简短清晰",
                                    "platform": platform,
                                    "reason": "钩子吸引力强，适合新手创作者"
                                },
                                {
                                    "version": "B",
                                    "title": f"{topic}｜剧情种草版",
                                    "description": "以生活化小故事切入，搭配情绪递进",
                                    "platform": platform,
                                    "reason": "综合评分最高，推荐首选"
                                },
                                {
                                    "version": "C",
                                    "title": f"{topic}｜深度测评版",
                                    "description": "多角度拆解主题细节，数据对比",
                                    "platform": platform,
                                    "reason": "适合深度粉丝，留存率高"
                                }
                            ]
                            st.session_state.schemes_list = mock_scheme
                            st.rerun()
                        else:
                            st.error(f"请求失败：{resp.text}")
                    except Exception as e:
                        st.error(f"请求异常：{e}")
    with col_tips:
        st.markdown("""
        <div class="info-tip">
        <b>💡 创作优化提示</b><br/>
        • 主题描述越具体，生成脚本质量越高<br/>
        • 抖音适配短平快钩子，小红书侧重图文氛围感<br/>
        • B站适合长剧情、深度科普类内容<br/>
        • 每次自动生成3套差异化方案，附带量化评分推荐
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 方案展示卡片
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📄 AI生成创作方案（A/B/C三套）</div>', unsafe_allow_html=True)
    if len(st.session_state.schemes_list) > 0:
        scheme_cols = st.columns(3)
        for idx, item in enumerate(st.session_state.schemes_list):
            with scheme_cols[idx]:
                st.markdown(f"""
                <div class="scheme-wrap">
                    <div class="version-badge">方案 {item['version']}</div>
                    <div class="scheme-name">{item['title']}</div>
                    <div class="scheme-desc">{item['description']}</div>
                    <span class="platform-tag">{item['platform']}</span>
                    <div class="recommend-panel">
                        <div class="rec-title">⭐ 系统推荐理由</div>
                        <div class="rec-text">{item['reason']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        col_export, col_compare = st.columns([1,1])
        with col_export:
            if st.button("📥 导出全部方案 Markdown", use_container_width=True):
                st.info("正在请求后端导出接口 /api/export，文件下载中...")
        with col_compare:
            if st.button("🔍 A/B方案对比分析", use_container_width=True):
                st.info("跳转方案对比模块，调用后端/compare接口进行维度打分对比")
    else:
        st.markdown('<div class="empty-container">暂无创作方案，填写上方参数点击「一键创作」生成内容 🎬</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ====================== 页面3：历史记录页面 ======================
def render_history_page():
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📋 历史创作会话记录</div>', unsafe_allow_html=True)
    if len(st.session_state.schemes_list) == 0:
        st.markdown('<div class="empty-container">暂无历史创作记录，前往工作台生成第一条内容</div>', unsafe_allow_html=True)
    else:
        st.dataframe(pd.DataFrame(st.session_state.schemes_list), use_container_width=True)
        st.download_button("导出历史记录CSV", data=pd.DataFrame(st.session_state.schemes_list).to_csv(index=False), file_name="创作历史记录.csv")
    st.markdown('</div>', unsafe_allow_html=True)

# ====================== 页面4：数据看板 ======================
def render_dashboard_page():
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📊 创作数据统计看板</div>', unsafe_allow_html=True)
    df = st.session_state.sample_stats
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(df, x="平台", y="数量", color="平台", title="各平台样例素材数量分布", color_discrete_sequence=["#7c3aed","#a78bfa","#c4b5fd"])
        st.plotly_chart(fig_bar, use_container_width=True)
    with col2:
        fig_pie = px.pie(df, values="数量", names="主题", title="创作主题分类占比")
        st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ====================== 主路由分发逻辑 ======================
def main():
    if not st.session_state.token:
        render_login_page()
    else:
        render_sidebar()
        if st.session_state.current_page == "📝 工作台":
            render_workbench()
        elif st.session_state.current_page == "📋 历史记录":
            render_history_page()
        elif st.session_state.current_page == "📊 数据看板":
            render_dashboard_page()

if __name__ == "__main__":
    main()