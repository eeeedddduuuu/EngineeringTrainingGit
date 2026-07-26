import streamlit as st
import requests
import time
import pandas as pd
import plotly.express as px

# ============================================================
# 全局页面配置
# ============================================================
st.set_page_config(
    page_title="AI 数字媒体创作助手",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 全局 CSS（暖色系，大圆角，现代字体）
# ============================================================
st.markdown("""
<style>
/* ----- 基础 ----- */
* {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}
.stApp {
    background: #faf6f0;
}
/* 顶部装饰条 */
.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #c97d4a, #d48c5c, #e0a87c, #d48c5c);
    z-index: 999999;
    box-shadow: 0 2px 12px rgba(180,130,80,0.22);
}
/* 间距修正 */
.block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
.stApp > div:first-child { padding-top: 0 !important; }
.stMarkdown { margin-bottom: 0 !important; }

/* ----- 通用卡片 ----- */
.primary-card {
    background: #ffffff;
    border-radius: 28px;
    padding: 32px 38px;
    margin-bottom: 26px;
    box-shadow: 0 16px 48px rgba(180,130,80,0.07), 0 4px 14px rgba(0,0,0,0.03);
    border: 1px solid rgba(235,215,195,0.5);
}
.card-title {
    color: #3d2c1b;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 22px;
    letter-spacing: -0.3px;
}

/* ----- 输入控件 ----- */
.stTextInput input, .stTextArea textarea, .stSelectbox select, .stFileUploader {
    background: #fcf9f5 !important;
    border: 1px solid #e8ddd0 !important;
    border-radius: 14px !important;
    padding: 14px 18px !important;
    font-size: 16px !important;
    transition: all 0.25s ease !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #d48c5c !important;
    box-shadow: 0 0 0 4px rgba(212,140,92,0.10) !important;
    outline: none;
    background: #fff !important;
}

/* ----- 按钮 ----- */
.stButton button {
    background: #d48c5c !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 40px !important;
    padding: 14px 36px !important;
    font-size: 16px !important;
    letter-spacing: 0.2px;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 16px rgba(212,140,92,0.25) !important;
}
.stButton button:hover {
    background: #c97d4a !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(212,140,92,0.35) !important;
}
.stButton button:active {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba(212,140,92,0.18) !important;
}

/* ----- 侧边栏 ----- */
section[data-testid="stSidebar"] {
    background: #fcf9f5 !important;
    border-right: 1px solid #f0e8de !important;
}
section[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    color: #5f4a34 !important;
    box-shadow: none !important;
    text-align: left !important;
    padding: 14px 20px !important;
    border-radius: 14px !important;
    font-weight: 500 !important;
    font-size: 16px !important;
    margin: 4px 0;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: #f0e5d8 !important;
    color: #d48c5c !important;
    transform: none;
    box-shadow: none !important;
}

/* ----- 方案卡片 ----- */
.scheme-wrap {
    background: #fcf9f5;
    border-radius: 22px;
    padding: 26px 22px;
    border: 1px solid #f0e8de;
    border-left: 4px solid #d48c5c;
    height: 100%;
    transition: all 0.3s ease;
}
.scheme-wrap:hover {
    border-color: #e0d0bc;
    border-left-color: #c97d4a;
    box-shadow: 0 8px 28px rgba(180,130,80,0.10);
}
.version-badge {
    display: inline-block;
    padding: 5px 18px;
    border-radius: 30px;
    font-size: 13px;
    font-weight: 700;
    background: #e8d9cc;
    color: #5f4a34;
    margin-bottom: 14px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.scheme-name {
    font-size: 20px;
    font-weight: 700;
    color: #3d2c1b;
    margin-bottom: 10px;
    letter-spacing: -0.2px;
}
.scheme-desc {
    color: #5f5a55;
    font-size: 15px;
    line-height: 1.75;
}
.platform-tag {
    display: inline-block;
    padding: 5px 16px;
    border-radius: 30px;
    font-size: 13px;
    font-weight: 500;
    background: #f0e5d8;
    color: #8a7a6a;
    margin-right: 6px;
    margin-top: 12px;
}

/* ----- 推荐框 ----- */
.recommend-panel {
    background: linear-gradient(135deg, #fcf9f5, #f5ede2);
    border-left: 4px solid #d48c5c;
    padding: 18px 22px;
    border-radius: 0 16px 16px 0;
    margin-top: 16px;
}
.rec-title {
    font-size: 13px; font-weight: 700; color: #d48c5c;
    letter-spacing: 1px; text-transform: uppercase;
}
.rec-text {
    font-size: 15px; color: #4d4035; margin-top: 6px; line-height: 1.7;
}

/* ----- 空状态 ----- */
.empty-container {
    text-align: center; padding: 72px 20px;
    color: #a09080; font-size: 17px;
}

/* ----- 提示框 ----- */
.info-tip {
    background: #f8f0e8; border-radius: 18px;
    padding: 22px 24px; border: 1px solid #f0e8de;
    color: #5f4a34; line-height: 1.9; font-size: 15px;
}

/* ----- 指标卡片 ----- */
.metric-card {
    background: #fcf9f5; padding: 22px 26px;
    border-radius: 22px; border: 1px solid #f0e8de;
    text-align: center;
}
.metric-card .metric-label {
    font-size: 14px; font-weight: 500; color: #8a7a6a;
    letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 4px;
}
.metric-card .metric-value {
    font-size: 38px; font-weight: 700; color: #3d2c1b;
}

/* ----- DataFrame ----- */
div[data-testid="stDataFrame"] {
    border-radius: 16px !important; overflow: hidden;
    border: 1px solid #f0e8de !important; font-size: 15px !important;
}

/* ----- 分割线 / 进度条 / 滚动条 ----- */
hr, .stDivider { border-color: #f0e8de !important; }
div[data-testid="stProgress"] > div {
    background: linear-gradient(90deg, #d48c5c, #e0a87c) !important;
    border-radius: 999px !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f0e8de; border-radius: 10px; }
::-webkit-scrollbar-thumb { background: #d4b896; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #d48c5c; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 常量 & Session 初始化
# ============================================================
API_BASE = "http://127.0.0.1:8000/api"

def init_session():
    defaults = {
        "token": None,
        "user": None,
        "current_page": "工作台",
        "schemes_list": [],
        "sample_stats": pd.DataFrame({
            "平台": ["抖音", "小红书", "B站", "抖音", "小红书", "B站", "抖音"],
            "主题": ["护肤", "美食", "数码", "旅行", "测评", "剧情", "好物"],
            "数量": [28, 36, 22, 18, 24, 16, 30]
        })
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ============================================================
# API 请求封装
# ============================================================
def api_request(path, method="GET", json_data=None):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        url = f"{API_BASE}{path}"
        if method == "GET":
            return requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            return requests.post(url, headers=headers, json=json_data, timeout=15)
        elif method == "PUT":
            return requests.put(url, headers=headers, json=json_data, timeout=15)
    except Exception as e:
        st.error(f"接口请求失败：{e}，请检查后端服务是否启动")
        return None

# ============================================================
# 登录 / 注册页（纯 HTML + CSS + JS，无白框）
# ============================================================
def render_login_page():
    # ---- 处理 URL 查询参数（表单提交） ----
    params = st.query_params
    action = params.get("_a", "")

    if action:
        username = params.get("_u", "")
        password = params.get("_p", "")

        if action == "login":
            resp = api_request("/auth/login", "POST",
                               {"username": username, "password": password})
            st.query_params.clear()
            if resp and resp.status_code == 200:
                data = resp.json()
                st.session_state.token = data["access_token"]
                st.session_state.user = {"username": data["username"]}
                st.rerun()
            else:
                detail = "账号或密码错误"
                if resp:
                    try: detail = resp.json().get("detail", detail)
                    except: detail = resp.text or detail
                st.session_state._login_error = detail
                st.rerun()

        elif action == "register":
            resp = api_request("/auth/register", "POST",
                               {"username": username, "password": password})
            st.query_params.clear()
            if resp and resp.status_code == 200:
                st.session_state._reg_success = True
                st.rerun()
            else:
                detail = "注册失败，用户名可能已存在"
                if resp:
                    try: detail = resp.json().get("detail", detail)
                    except: detail = resp.text or detail
                st.session_state._reg_error = detail
                st.rerun()

    # ---- 读取 flash 消息 ----
    login_error   = st.session_state.pop("_login_error", "")
    reg_error     = st.session_state.pop("_reg_error", "")
    reg_success   = st.session_state.pop("_reg_success", False)

    error_html          = ""
    login_checked       = "checked"
    register_checked    = ""

    if login_error:
        error_html = f'<div class="auth-msg error">{login_error}</div>'
    elif reg_error:
        error_html = f'<div class="auth-msg error">{reg_error}</div>'
        login_checked    = ""
        register_checked = "checked"
    elif reg_success:
        error_html = '<div class="auth-msg success">注册完成！请切换到"用户登录"标签页登录</div>'

    login_checked_attr    = "checked" if login_checked    else ""
    register_checked_attr = "checked" if register_checked else ""

    # ---- 完整 HTML 文档 ----
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  background:#faf6f0; min-height:100vh;
  display:flex; flex-direction:column; align-items:center;
  justify-content:center; padding:40px 20px;
}}
.brand-title {{
  font-size:36px; font-weight:800; color:#3d2c1b;
  letter-spacing:-0.5px; margin-bottom:8px; text-align:center;
}}
.brand-subtitle {{
  font-size:14px; color:#8a7a6a; letter-spacing:3px;
  font-weight:500; margin-bottom:40px; text-align:center;
}}
.auth-card {{
  width:100%; max-width:440px; background:#ffffff;
  border-radius:24px; padding:36px 34px;
  box-shadow:0 20px 60px rgba(180,130,80,0.08), 0 4px 16px rgba(0,0,0,0.03);
  border:1px solid rgba(235,215,195,0.5);
}}
/* 纯 CSS 标签切换 */
.tab-group input[type="radio"] {{ display:none; }}
.tab-header {{
  display:flex; background:#f5ede2; border-radius:16px;
  padding:4px; margin-bottom:28px;
}}
.tab-label {{
  flex:1; text-align:center; padding:12px 16px; border-radius:13px;
  cursor:pointer; font-size:16px; font-weight:500; color:#8a7a6a;
  transition:all 0.3s ease; user-select:none; white-space:nowrap;
}}
.tab-label:hover {{ color:#5f4a34; }}
#tab-login:checked ~ .tab-header label[for="tab-login"],
#tab-register:checked ~ .tab-header label[for="tab-register"] {{
  background:#fff; color:#3d2c1b; font-weight:600;
  box-shadow:0 2px 8px rgba(0,0,0,0.05);
}}
.tab-panel {{ display:none; }}
#tab-login:checked ~ #panel-login {{ display:block; }}
#tab-register:checked ~ #panel-register {{ display:block; }}
/* 表单 */
.form-group {{ margin-bottom:16px; }}
.form-input {{
  width:100%; padding:14px 18px; border:1px solid #e8ddd0;
  border-radius:14px; font-size:16px;
  font-family:'Inter','Segoe UI',system-ui,sans-serif;
  background:#fcf9f5; color:#3d2c1b; transition:all 0.25s ease; outline:none;
}}
.form-input:focus {{
  border-color:#d48c5c; box-shadow:0 0 0 4px rgba(212,140,92,0.10); background:#fff;
}}
.form-input::placeholder {{ color:#a09080; font-size:15px; }}
.submit-btn {{
  width:100%; padding:14px; background:#d48c5c; color:white;
  border:none; border-radius:40px; font-size:17px; font-weight:600;
  cursor:pointer; transition:all 0.25s ease;
  box-shadow:0 4px 16px rgba(212,140,92,0.25);
  letter-spacing:0.5px; font-family:'Inter','Segoe UI',system-ui,sans-serif;
  margin-top:6px;
}}
.submit-btn:hover {{
  background:#c97d4a; box-shadow:0 6px 24px rgba(212,140,92,0.35);
  transform:translateY(-1px);
}}
.submit-btn:active {{ transform:translateY(0); box-shadow:0 2px 8px rgba(212,140,92,0.18); }}
.submit-btn:disabled {{ opacity:0.65; cursor:not-allowed; transform:none; }}
/* 消息 */
.auth-msg {{
  padding:12px 18px; border-radius:12px; font-size:15px;
  font-weight:500; margin-bottom:20px;
  animation:slideDown 0.3s ease;
}}
@keyframes slideDown {{
  from {{ opacity:0; transform:translateY(-8px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
.auth-msg.error   {{ background:#fef2f2; color:#dc2626; border:1px solid #fecaca; }}
.auth-msg.success {{ background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; }}
.footer-text {{
  color:#a09080; font-size:14px; margin-top:28px;
  text-align:center; letter-spacing:0.5px;
}}
</style>
</head>
<body>

<h1 class="brand-title">AI 数字媒体创作助手</h1>
<p class="brand-subtitle">MULTIMEDIA AI CREATOR</p>

<div class="auth-card">
  {error_html}
  <div class="tab-group">
    <input type="radio" name="auth-tab" id="tab-login" {login_checked_attr}>
    <input type="radio" name="auth-tab" id="tab-register" {register_checked_attr}>

    <div class="tab-header">
      <label for="tab-login" class="tab-label">用户登录</label>
      <label for="tab-register" class="tab-label">新用户注册</label>
    </div>

    <div class="tab-panel" id="panel-login">
      <form onsubmit="return handleLogin(event)">
        <div class="form-group">
          <input type="text" class="form-input" id="login-username"
                 placeholder="输入你的账号" autocomplete="username" autocorrect="off">
        </div>
        <div class="form-group">
          <input type="password" class="form-input" id="login-password"
                 placeholder="输入密码" autocomplete="current-password">
        </div>
        <button type="submit" class="submit-btn" id="login-btn">立即登录</button>
      </form>
    </div>

    <div class="tab-panel" id="panel-register">
      <form onsubmit="return handleRegister(event)">
        <div class="form-group">
          <input type="text" class="form-input" id="reg-username"
                 placeholder="自定义账号" autocomplete="off" autocorrect="off">
        </div>
        <div class="form-group">
          <input type="password" class="form-input" id="reg-password"
                 placeholder="设置密码（6位以上字符）" autocomplete="new-password">
        </div>
        <div class="form-group">
          <input type="password" class="form-input" id="reg-password2"
                 placeholder="再次输入密码" autocomplete="new-password">
        </div>
        <button type="submit" class="submit-btn" id="reg-btn">完成注册</button>
      </form>
    </div>
  </div>
</div>

<p class="footer-text">AI 驱动 &middot; 一键生成 &middot; 多平台适配</p>

<script>
function handleLogin(e) {{
  e.preventDefault();
  var u = document.getElementById('login-username').value.trim();
  var p = document.getElementById('login-password').value;
  if (!u || !p) {{ showFlash('请填写完整账号密码！','error'); return false; }}
  setLoading('login-btn', true);
  submit('login', u, p);
  return false;
}}
function handleRegister(e) {{
  e.preventDefault();
  var u = document.getElementById('reg-username').value.trim();
  var p = document.getElementById('reg-password').value;
  var p2 = document.getElementById('reg-password2').value;
  if (!u || !p) {{ showFlash('账号密码不能为空！','error'); return false; }}
  if (p !== p2) {{ showFlash('两次输入密码不一致，请重新填写','error'); return false; }}
  if (p.length < 6) {{ showFlash('密码长度不能少于 6 位字符','error'); return false; }}
  setLoading('reg-btn', true);
  submit('register', u, p);
  return false;
}}
function submit(action, username, password) {{
  var p = new URLSearchParams();
  p.set('_a', action); p.set('_u', username); p.set('_p', password);
  window.location.search = '?' + p.toString();
}}
function showFlash(msg, type) {{
  var old = document.querySelector('.auth-msg');
  if (old) old.remove();
  var card = document.querySelector('.auth-card');
  var div = document.createElement('div');
  div.className = 'auth-msg ' + type;
  div.textContent = msg;
  card.insertBefore(div, card.firstChild);
  setTimeout(function() {{ if (div.parentNode) div.remove(); }}, 4000);
}}
function setLoading(btnId, loading) {{
  var btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {{ btn.disabled=true; btn._origText=btn.textContent; btn.textContent='处理中...'; }}
  else {{ btn.disabled=false; if (btn._origText) btn.textContent=btn._origText; }}
}}
</script>
</body>
</html>"""

    st.html(html_doc)


# ============================================================
# 侧边栏导航
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("## AI 创作助手")
        st.divider()
        if st.session_state.user:
            username = st.session_state.user.get("username", "未知") \
                       if isinstance(st.session_state.user, dict) \
                       else st.session_state.user
            st.markdown(f"当前用户：**{username}**")
        st.divider()

        for page in ["工作台", "历史记录", "数据看板"]:
            if st.button(page, use_container_width=True, key=f"nav_{page}"):
                st.session_state.current_page = page
                st.rerun()

        st.divider()
        if st.button("退出登录", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.schemes_list = []
            st.rerun()


# ============================================================
# 创作工作台
# ============================================================
def render_workbench():
    # ---- 输入区域 ----
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">创作工作台</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])

    with col_left:
        with st.form("create_form"):
            topic = st.text_input("创作主题", placeholder="例：秋季平价护肤攻略、二次元游戏剧情脚本")
            audience = st.text_input("目标受众", placeholder="例：20-30岁学生、数码发烧友、宝妈群体")

            c1, c2, c3 = st.columns(3)
            with c1:
                platform = st.selectbox("发布平台", ["抖音", "小红书", "B站"])
            with c2:
                duration = st.selectbox("视频时长", ["15秒", "30秒", "60秒"])
            with c3:
                style = st.selectbox("内容风格", ["干货科普", "轻娱乐", "情感走心", "剧情故事", "测评种草"])

            st.file_uploader("上传参考素材（图片/音频）", accept_multiple_files=True, key="uploader")
            submitted = st.form_submit_button("启动 AI 创作", use_container_width=True)

        if submitted:
            if not topic:
                st.error("创作主题为必填项，请完善！")
            else:
                platform_map = {"抖音": "douyin", "小红书": "xiaohongshu", "B站": "bilibili"}
                duration_map = {"15秒": "15s", "30秒": "30s", "60秒": "60s"}
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
                    if resp.status_code in (200, 202):
                        data = resp.json()
                        st.success(f"任务已提交，任务ID：{data.get('task_id', '未知')}")
                        st.session_state.schemes_list = [
                            {
                                "version": "A",
                                "title": f"{topic} - 简洁干货版",
                                "description": "开篇直击痛点，结构简短清晰，快速抓住观众注意力。",
                                "platform": platform,
                                "reason": "钩子吸引力强，适合新手创作者快速上手"
                            },
                            {
                                "version": "B",
                                "title": f"{topic} - 剧情种草版",
                                "description": "以生活化小故事切入，搭配情绪递进，自然植入产品。",
                                "platform": platform,
                                "reason": "综合评分最高，推荐首选，转化效果稳定"
                            },
                            {
                                "version": "C",
                                "title": f"{topic} - 深度测评版",
                                "description": "多角度拆解主题细节，数据对比，专业可信。",
                                "platform": platform,
                                "reason": "适合深度粉丝群体，用户留存率高"
                            }
                        ]
                        st.rerun()
                    else:
                        st.error(f"请求失败：{resp.text}")
                except Exception as e:
                    st.error(f"请求异常：{e}")

    with col_right:
        st.markdown("""
        <div class="info-tip">
        <b>创作优化提示</b><br/><br/>
        &bull; 主题描述越具体，生成脚本质量越高<br/>
        &bull; 抖音适配短平快钩子，小红书侧重图文氛围感<br/>
        &bull; B站适合长剧情、深度科普类内容<br/>
        &bull; 每次自动生成 3 套差异化方案，附带推荐理由
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- 方案展示区域 ----
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">创作方案</div>', unsafe_allow_html=True)

    if len(st.session_state.schemes_list) > 0:
        cols = st.columns(3)
        for idx, item in enumerate(st.session_state.schemes_list):
            with cols[idx]:
                st.markdown(f"""
                <div class="scheme-wrap">
                    <div class="version-badge">方案 {item['version']}</div>
                    <div class="scheme-name">{item['title']}</div>
                    <div class="scheme-desc">{item['description']}</div>
                    <span class="platform-tag">{item['platform']}</span>
                    <div class="recommend-panel">
                        <div class="rec-title">系统推荐理由</div>
                        <div class="rec-text">{item['reason']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        ec, cc = st.columns([1, 1])
        with ec:
            if st.button("导出全部方案 (Markdown)", use_container_width=True):
                st.info("正在请求后端导出接口 /api/export ...")
        with cc:
            if st.button("A/B 方案对比分析", use_container_width=True):
                st.info("跳转方案对比模块，调用后端 /compare 接口进行维度打分对比")
    else:
        st.markdown(
            '<div class="empty-container">暂无创作方案，填写上方参数后点击「启动 AI 创作」生成内容</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 历史记录
# ============================================================
def render_history_page():
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">历史创作记录</div>', unsafe_allow_html=True)

    if len(st.session_state.schemes_list) == 0:
        st.markdown(
            '<div class="empty-container">暂无历史创作记录，前往工作台生成第一条内容</div>',
            unsafe_allow_html=True
        )
    else:
        df = pd.DataFrame(st.session_state.schemes_list)
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "导出历史记录 (CSV)",
            data=df.to_csv(index=False),
            file_name="创作历史记录.csv"
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 数据看板
# ============================================================
def render_dashboard_page():
    st.markdown('<div class="primary-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">创作数据统计</div>', unsafe_allow_html=True)

    df = st.session_state.sample_stats

    # KPI 指标
    mc = st.columns(4)
    for i, (label, val) in enumerate([
        ("素材总数", len(df)),
        ("覆盖平台", df["平台"].nunique()),
        ("主题类型", df["主题"].nunique()),
        ("本周新增", 8),
    ]):
        with mc[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        fig1 = px.bar(
            df, x="平台", y="数量", color="平台",
            title="各平台素材数量分布",
            color_discrete_sequence=["#d48c5c", "#e0a87c", "#e8c9a8"]
        )
        fig1.update_layout(
            height=420,
            title_font_size=20,
            xaxis_title_font_size=15,
            yaxis_title_font_size=15,
            xaxis_tickfont_size=14,
            yaxis_tickfont_size=14,
            legend_font_size=14,
            margin=dict(t=50, b=40, l=40, r=20),
        )
        st.plotly_chart(fig1, use_container_width=True)

    with right:
        fig2 = px.pie(
            df, values="数量", names="主题",
            title="创作主题分类占比",
            color_discrete_sequence=[
                "#d48c5c", "#e0a87c", "#e8c9a8",
                "#c97d4a", "#f0c8a0", "#e8b888", "#d4a070"
            ]
        )
        fig2.update_layout(
            height=420,
            title_font_size=20,
            legend_font_size=14,
            margin=dict(t=50, b=40, l=20, r=20),
        )
        fig2.update_traces(textfont_size=14)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 主路由
# ============================================================
def main():
    if not st.session_state.token:
        render_login_page()
    else:
        render_sidebar()
        page = st.session_state.current_page
        if page == "工作台":
            render_workbench()
        elif page == "历史记录":
            render_history_page()
        elif page == "数据看板":
            render_dashboard_page()


if __name__ == "__main__":
    main()
