"""
AI 数字媒体创作助手 — 前端 v4
完整功能 · 全后端对接 · 专业 UI
"""
import streamlit as st
import requests
import time
import pandas as pd
import plotly.express as px

# ====================== 配置 ======================
API = "http://127.0.0.1:8000/api"
API_BASE = API  # 兼容远程 P5 数据看板的变量名

st.set_page_config(page_title="AI 数字媒体创作助手", page_icon="🎬", layout="wide")

# ====================== 主题 CSS ======================
st.markdown("""
<style>
    [data-testid="stSidebar"] { background: rgba(124,58,237,0.02); }
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #8b5cf6) !important;
        color: #fff !important; border: none !important;
        border-radius: 10px !important; font-weight: 600 !important;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #6d28d9, #7c3aed) !important; }
    .card {
        border: 1px solid rgba(128,128,128,0.15); border-radius: 14px;
        padding: 20px 24px; margin-bottom: 16px; height: 100%;
    }
    .card:hover { border-color: rgba(124,58,237,0.3); }
    .metric-box {
        text-align: center; padding: 20px; border-radius: 14px;
        background: rgba(124,58,237,0.04); border: 1px solid rgba(124,58,237,0.1);
    }
    .metric-box h2 { margin: 0; color: #7c3aed; }
</style>
""", unsafe_allow_html=True)

# ====================== 数据清洗 ======================
def safe_list(v): return v if isinstance(v, list) else []
def safe_dict(v): return v if isinstance(v, dict) else {}
def safe_str(v): return v if isinstance(v, str) else ""

def clean_scheme(s):
    """确保 scheme 数据字段非 None"""
    return {
        **s,
        "scenes": safe_list(s.get("scenes")),
        "hashtags": safe_list(s.get("hashtags")),
        "storyboard_json": safe_dict(s.get("storyboard_json")),
        "raw_markdown": safe_str(s.get("raw_markdown")),
        "cover_text": safe_str(s.get("cover_text")),
        "hook": safe_str(s.get("hook")),
        "title": safe_str(s.get("title")),
        "recommendation_reason": safe_str(s.get("recommendation_reason")),
    }

# ====================== Session ======================
def init():
    for k, v in {
        "token": None, "user": None, "page": "工作台",
        "task_id": None, "task_status": None, "schemes": [],
    }.items():
        if k not in st.session_state: st.session_state[k] = v
init()

# ====================== API ======================
def api(path, method="GET", data=None):
    h = {}
    if st.session_state.token: h["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        if method == "GET":
            r = requests.get(f"{API}{path}", headers=h, params=data, timeout=30)
        else:
            r = requests.post(f"{API}{path}", headers=h, json=data, timeout=60)
        return r
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        st.error(f"请求异常: {e}")
        return None

# ====================== 登录 ======================
def login_page():
    _, c, _ = st.columns([1, 1.5, 1])
    with c:
        st.title("🎬 AI 数字媒体创作助手")
        st.caption("智能脚本生成 · 多平台适配 · 数据驱动的创作决策")

        t1, t2 = st.tabs(["🔐 登录", "📝 注册"])
        with t1:
            with st.form("login"):
                u = st.text_input("用户名")
                p = st.text_input("密码", type="password")
                if st.form_submit_button("登录", use_container_width=True):
                    if not u or not p:
                        st.warning("请填写完整")
                    else:
                        r = api("/auth/login", "POST", {"username": u, "password": p})
                        if r and r.status_code == 200:
                            d = r.json()
                            st.session_state.token = d["access_token"]
                            st.session_state.user = d["username"]
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
        with t2:
            with st.form("register"):
                ru = st.text_input("用户名", placeholder="3-20位字母数字")
                rp = st.text_input("密码", type="password", placeholder="至少6位")
                rp2 = st.text_input("确认密码", type="password")
                if st.form_submit_button("注册", use_container_width=True):
                    if not ru or not rp: st.warning("请填写完整")
                    elif rp != rp2: st.error("两次密码不一致")
                    elif len(rp) < 6: st.error("密码至少6位")
                    else:
                        r = api("/auth/register", "POST", {"username": ru, "password": rp})
                        if r and r.status_code == 200: st.success("注册成功，请登录")
                        else: st.error("注册失败，用户名可能已存在")

# ====================== 公共组件 ======================
def show_scheme_cards(schemes, show_detail=True, show_export=True):
    """展示方案卡片（三列布局）"""
    if not schemes: return
    schemes = [clean_scheme(s) for s in schemes]
    cols = st.columns(len(schemes))
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, s in enumerate(schemes):
        rank = s.get("rank", i + 1)
        with cols[i]:
            st.markdown(f"""
            <div class="card">
                <span style="color:#7c3aed;font-weight:700;font-size:14px;">
                    方案 {s.get('version', '?')} {medals.get(rank, '')}
                </span>
                <h4>{s.get('title', '未命名')}</h4>
                <p style="font-size:13px;opacity:0.7;line-height:1.6;">{s.get('hook', '')[:120]}</p>
                <p>
                    <b style="color:#16a34a;">⭐ {s.get('score', 0)}</b>
                    &nbsp; 🎬 {len(s['scenes'])} 场景 &nbsp;
                    {rank}/{len(schemes)}
                </p>
                <p style="font-size:12px;opacity:0.5;">🏷️ {' '.join(s['hashtags'][:3])}</p>
            </div>
            """, unsafe_allow_html=True)

            if show_detail:
                with st.expander("📋 完整详情"):
                    st.markdown(f"**标题：** {s.get('title')}")
                    st.markdown(f"**钩子：** {s.get('hook')}")
                    st.markdown(f"**封面：** {s.get('cover_text', '无')}")
                    st.markdown(f"**标签：** {' '.join(s.get('hashtags') or [])}")
                    st.divider()
                    st.markdown("**🎬 分镜脚本：**")
                    scenes = s.get("scenes") or []
                    # 优先展示结构化 scenes；无 scenes 则从 storyboard_json/raw_markdown 渲染
                    raw_md = s.get("raw_markdown") or (s.get("storyboard_json") or {}).get("raw_markdown", "")
                    if scenes:
                        for sc in scenes:
                            vo = sc.get('voiceover', '')
                            st.markdown(
                                f"**{sc.get('seq')}.** [{sc.get('type','')}] "
                                f"`{sc.get('duration','')}` — {sc.get('description','')}"
                            )
                            if vo: st.caption(f"🎤 {vo[:200]}")
                    if raw_md:
                        st.markdown("**📝 完整脚本预览：**")
                        st.markdown(raw_md[:3000])
                        if len(raw_md) > 3000:
                            st.caption(f"（共 {len(raw_md)} 字符，下载 Markdown 查看完整内容）")
                    if not scenes and not raw_md:
                        st.info("暂无详细脚本数据")
                    reason = s.get('recommendation_reason', '')
                    if reason:
                        st.markdown(f"**推荐理由：** {reason}")

            if show_export and s.get("id"):
                r = api(f"/export/{s['id']}?format=md")
                if r and r.status_code == 200:
                    st.download_button(
                        f"📥 下载方案 {s.get('version','?')}",
                        r.text, f"方案{s.get('version','')}_{s['id']}.md",
                        mime="text/markdown", key=f"dl_{s.get('id','')}",
                        use_container_width=True,
                    )

# ====================== 页面4：数据看板（P5 真实数据驱动） ======================
def render_dashboard_page():
    st.markdown('<div class="card-title">📊 样例数据统计看板</div>', unsafe_allow_html=True)

    # ── 从后端加载真实数据 ──
    try:
        resp = requests.get(
            f"{API_BASE}/stats/samples",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            stats = resp.json()
        else:
            st.error(f"统计数据加载失败: HTTP {resp.status_code}")
            return
    except Exception as e:
        st.error(f"无法连接后端: {e}")
        return

    total = stats.get("total_samples", 0)
    topics = stats.get("topic_distribution", [])
    platforms = stats.get("platform_distribution", [])
    trends = stats.get("monthly_trends", [])

    if total == 0:
        st.warning("暂无统计数据，请先运行 init_db.py 导入样例数据")
        return

    # ── 指标卡 ──
    cols = st.columns(4)
    with cols[0]:
        st.metric("📦 样例总数", f"{total} 条")
    with cols[1]:
        st.metric("🏷️ 类别数", f"{len(topics)} 类")
    with cols[2]:
        st.metric("📱 平台数", f"{len(platforms)} 个")
    with cols[3]:
        st.metric("🗓️ 月度跨度", f"{len(trends)} 个月")

    st.divider()

    # ── 第一行：主题分布 + 平台分布 ──
    st.markdown("### 🎨 主题与平台分布")
    r1l, r1r = st.columns(2)

    with r1l:
        df_topic = pd.DataFrame(topics)
        colors = ["#4ECDC4", "#FF6B6B", "#FFE66D", "#95E1D3", "#F38181", "#AA96DA"]
        fig = px.pie(
            df_topic, values="count", names="name",
            color_discrete_sequence=colors, hole=0.4,
            title="样例主题分布",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=420, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with r1r:
        df_plat = pd.DataFrame(platforms)
        plat_names = {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}
        df_plat["平台名"] = df_plat["platform"].map(plat_names).fillna(df_plat["platform"])
        fig = px.bar(
            df_plat, x="平台名", y="count", color="平台名",
            color_discrete_sequence=["#FF6B6B", "#4ECDC4", "#FFE66D"],
            text="count", title="各平台样例数量",
        )
        fig.update_traces(textposition="outside", textfont_size=14)
        fig.update_layout(height=420, showlegend=False, xaxis_title="", yaxis_title="",
                          margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 第二行：月度趋势 + 类别对比 ──
    st.markdown("### 📅 趋势与对比")
    r2l, r2r = st.columns(2)

    with r2l:
        if trends:
            df_trend = pd.DataFrame(trends)
            fig = px.area(
                df_trend, x="month", y="count",
                title="月度发布趋势",
                markers=True,
            )
            fig.update_traces(line_color="#FF6B6B", fillcolor="rgba(255,107,107,0.15)")
            fig.update_layout(height=420, xaxis_title="", yaxis_title="",
                              margin=dict(t=40, b=10, l=10, r=10))
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无趋势数据")

    with r2r:
        df_sorted = df_topic.sort_values("count", ascending=True)
        fig = px.bar(
            df_sorted, y="name", x="count", orientation="h",
            color="name", color_discrete_sequence=colors,
            text="count", title="类别数量对比",
        )
        fig.update_traces(textposition="outside", textfont_size=14)
        fig.update_layout(height=420, showlegend=False, xaxis_title="", yaxis_title="",
                          margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 第三行：占比环形图 + 数据表 ──
    st.markdown("### 🔍 多维度明细")
    r3l, r3r = st.columns([1, 1.2])

    with r3l:
        fig = px.pie(
            df_topic, values="count", names="name",
            color_discrete_sequence=colors, hole=0.6,
            title="类别占比总览",
        )
        fig.update_traces(textposition="outside", textinfo="percent+label",
                          pull=[0.03] * len(df_topic))
        fig.update_layout(height=400, showlegend=False,
                          margin=dict(t=40, b=10, l=10, r=60))
        fig.add_annotation(text=f"总计<br>{total}条", x=0.5, y=0.5, font_size=22, showarrow=False)
        st.plotly_chart(fig, use_container_width=True)

    with r3r:
        if trends:
            df_m = pd.DataFrame(trends).tail(12).sort_values("month", ascending=False)
            df_m.columns = ["月份", "数量"]
            df_m["环比变化"] = df_m["数量"].diff(-1).fillna(0).astype(int)
            st.dataframe(df_m, use_container_width=True, hide_index=True, height=400)

    st.caption(f"数据来源: samples.xlsx（{total} 条样例）| P5 数据/知识库模块 | Plotly 图表实时渲染")

# ====================== 创作工作台 ======================
def workbench_page():
    st.title("🚀 创作工作台")
    st.caption("填写创作参数，AI Agent 流水线将自动生成 3 套差异化方案")

    # 输入区
    with st.container(border=True):
        with st.form("create"):
            c1, c2 = st.columns(2)
            with c1:
                topic = st.text_input("创作主题 *", placeholder="例：秋季护肤好物推荐")
                audience = st.text_input("目标受众", placeholder="例：25-35岁职场女性")
            with c2:
                platform = st.selectbox("发布平台", ["抖音", "小红书", "B站"])
                duration = st.selectbox("视频时长", ["30秒", "60秒", "3分钟"])
            style = st.selectbox("内容风格", ["干货科普", "轻娱乐", "情感走心", "剧情故事", "测评种草"])
            go = st.form_submit_button("✨ 一键启动 AI 创作", use_container_width=True)

            if go:
                if not topic:
                    st.error("请填写创作主题")
                else:
                    pm = {"抖音": "douyin", "小红书": "xiaohongshu", "B站": "bilibili"}
                    dm = {"30秒": "30s", "60秒": "60s", "3分钟": "3min"}
                    r = api("/creation/start", "POST", {
                        "topic": topic, "target_audience": audience or "通用",
                        "platform": pm[platform], "duration": dm[duration], "style": style,
                    })
                    if r is None:
                        st.error("❌ 无法连接后端服务 (http://127.0.0.1:8000)")
                    elif r.status_code in (200, 202):
                        d = r.json()
                        st.session_state.task_id = d["task_id"]
                        st.session_state.task_status = d["status"]
                        st.session_state.schemes = []
                        st.success("任务已提交，Agent 正在创作中...")
                        st.rerun()
                    else:
                        st.error(f"提交失败 HTTP {r.status_code}: {r.text[:200]}")

    # 任务轮询
    if st.session_state.task_id and st.session_state.task_status not in ("completed", "failed"):
        placeholder = st.empty()
        progress_bar = st.progress(0, "Agent 流水线处理中...")
        for i in range(30):
            r = api(f"/task/{st.session_state.task_id}/status")
            if not r: break
            d = r.json()
            st.session_state.task_status = d["status"]
            progress_bar.progress(min((i + 1) / 15, 0.95), d.get("progress", "处理中..."))
            if d["status"] == "completed":
                result = d.get("result", {})
                st.session_state.schemes = result.get("schemes", [])
                st.session_state.task_status = "completed"
                placeholder.empty(); progress_bar.empty()
                st.success(f"🎉 创作完成！AI 生成了 {len(st.session_state.schemes)} 个方案")
                st.rerun()
            elif d["status"] == "failed":
                placeholder.error(f"创作失败：{d.get('result', {}).get('detail', '未知错误')}")
                st.session_state.task_status = "failed"
                progress_bar.empty()
                st.rerun()
            time.sleep(3)
        else:
            progress_bar.empty()
            st.warning("处理时间较长，后台仍在运行，稍后刷新查看")

    # 方案展示
    if st.session_state.schemes:
        st.divider()
        st.subheader(f"📄 生成方案（{len(st.session_state.schemes)} 个）")
        show_scheme_cards(st.session_state.schemes)

        # 操作栏
        c1, c2, c3 = st.columns(3)
        with c1:
            ids = [s["id"] for s in st.session_state.schemes if "id" in s]
            if len(ids) >= 2 and st.button("🔍 A/B 方案对比分析", use_container_width=True):
                r = api("/schemes/compare", "POST", {"scheme_ids": ids[:2]})
                if r and r.status_code == 200:
                    st.info(r.json().get("diff_summary", "对比结果获取中..."))
        with c2:
            if st.button("📦 导出全部方案 JSON", use_container_width=True):
                import json as _json
                st.download_button("下载 JSON", _json.dumps(st.session_state.schemes, ensure_ascii=False, indent=2),
                                   "全部方案.json", "application/json", use_container_width=True)
        with c3:
            if st.button("🔄 开始新创作", use_container_width=True):
                st.session_state.task_id = None
                st.session_state.task_status = None
                st.session_state.schemes = []
                st.rerun()

    if not st.session_state.task_id:
        st.info("👆 填写主题和参数，点击「一键启动 AI 创作」")

# ====================== 方案浏览 ======================
def schemes_page():
    st.title("📋 方案浏览")
    st.caption("查看历史会话的所有生成方案，支持对比和导出")

    r = api("/history?page=1&size=50")
    if not r or r.status_code != 200:
        st.error("无法加载历史记录")
        return

    items = r.json().get("items", [])
    if not items:
        st.info("暂无创作记录，请前往工作台生成内容")
        return

    # 选会话
    sid = st.selectbox(
        "选择创作会话",
        [it["session_id"] for it in items],
        format_func=lambda x: f"#{x} — {next((i['topic'] for i in items if i['session_id'] == x), '')} ({next((i.get('scheme_count', 0) for i in items if i['session_id'] == x), 0)}个方案)"
    )

    if st.button("🔍 加载方案", use_container_width=True, type="primary"):
        r2 = api(f"/schemes?session_id={sid}")
        if r2 and r2.status_code == 200:
            data = r2.json()
            schemes = data.get("schemes", [])
            if schemes:
                st.success(f"会话 #{sid} — {data.get('topic', '')}")
                show_scheme_cards(schemes)
                # 一键对比
                ids = [s["id"] for s in schemes if "id" in s]
                if len(ids) >= 2 and st.button("🔍 A/B 方案对比", use_container_width=True):
                    r3 = api("/schemes/compare", "POST", {"scheme_ids": ids[:2]})
                    if r3 and r3.status_code == 200:
                        st.info(r3.json().get("diff_summary", ""))
            else:
                st.warning("该会话无方案数据")

# ====================== 历史记录 ======================
def history_page():
    st.title("📜 历史记录")
    st.caption("浏览和管理所有创作会话")

    page = st.number_input("页码", 1, 100, 1, key="hist_page")
    r = api("/history", "GET", {"page": page, "size": 10})
    if not r or r.status_code != 200:
        st.error("无法加载历史记录")
        return

    data = r.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    if not items:
        st.info("暂无创作记录")
        return

    st.metric("总创作会话", total)
    st.divider()

    rows = []
    for it in items:
        rows.append({
            "会话ID": it["session_id"],
            "主题": it.get("topic", ""),
            "平台": {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}.get(it.get("platform", ""), ""),
            "方案数": f"{it.get('scheme_count', 0)}个",
            "状态": {"completed": "✅完成", "pending": "⏳排队", "processing": "🔄处理中", "failed": "❌失败"}.get(it.get("status", ""), it.get("status", "")),
            "创建时间": it.get("created_at", "")[:19],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 选会话查看方案
    st.divider()
    sel = st.selectbox("选择一个会话查看详情", [it["session_id"] for it in items],
                       format_func=lambda x: f"#{x} — {next((i['topic'] for i in items if i['session_id'] == x), '')}")
    if st.button("📋 查看方案", use_container_width=True):
        r2 = api(f"/schemes?session_id={sel}")
        if r2 and r2.status_code == 200:
            schemes = r2.json().get("schemes", [])
            if schemes:
                show_scheme_cards(schemes)

# ====================== 数据看板 ======================
def dashboard_page():
    st.title("📊 数据看板")
    st.caption("知识库样例数据统计分析")

    r = api("/stats/samples")
    if not r or r.status_code != 200:
        st.warning("无法获取统计数据")
        return

    d = r.json()

    # 指标行
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-box"><h3>{d.get("total_samples", 0)}</h3><p>样例总数</p></div>', unsafe_allow_html=True)
    td = d.get("topic_distribution", [])
    with m2:
        st.markdown(f'<div class="metric-box"><h3>{len(td)}</h3><p>主题分类</p></div>', unsafe_allow_html=True)
    pd_data = d.get("platform_distribution", [])
    with m3:
        st.markdown(f'<div class="metric-box"><h3>{len(pd_data)}</h3><p>覆盖平台</p></div>', unsafe_allow_html=True)
    md = d.get("monthly_trends", [])
    with m4:
        st.markdown(f'<div class="metric-box"><h3>{len(md)}</h3><p>月度数据点</p></div>', unsafe_allow_html=True)

    # 图表
    c1, c2 = st.columns(2)
    with c1:
        if td:
            st.plotly_chart(
                px.pie(pd.DataFrame(td), values="count", names="name", title="主题分布",
                       color_discrete_sequence=px.colors.sequential.Purples_r),
                use_container_width=True
            )
        if md:
            st.plotly_chart(
                px.line(pd.DataFrame(md), x="month", y="count", title="月度趋势", markers=True,
                        color_discrete_sequence=["#7c3aed"]),
                use_container_width=True
            )
    with c2:
        if pd_data:
            labels = {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}
            df = pd.DataFrame(pd_data)
            df["平台"] = df["platform"].map(labels).fillna(df["platform"])
            st.plotly_chart(
                px.bar(df, x="平台", y="count", color="平台", title="平台分布",
                       color_discrete_sequence=["#7c3aed", "#a78bfa", "#c4b5fd"]),
                use_container_width=True
            )

# ====================== 知识库搜索 ======================
def knowledge_page():
    st.title("🔍 知识库搜索")
    st.caption("语义检索 50 条样例数据，查看相似内容和引用来源")

    with st.container(border=True):
        q = st.text_input("搜索关键词", placeholder="例：短视频脚本、游戏剧情、品牌宣传")
        top = st.slider("返回条数", 1, 20, 5)
        if st.button("🔍 搜索", use_container_width=True, type="primary"):
            if q:
                r = api(f"/knowledge/search?q={q}&top_k={top}")
                if r and r.status_code == 200:
                    results = r.json().get("results", [])
                    if results:
                        st.success(f"找到 {len(results)} 条结果")
                        for item in results:
                            with st.container(border=True):
                                c1, c2 = st.columns([4, 1])
                                with c1:
                                    st.markdown(f"**{item.get('title', '')}**")
                                    st.caption(item.get("content_snippet", "")[:200])
                                    st.markdown(
                                        f"🏷️ {' '.join(item.get('tags') or [])}  "
                                        f"| 📱 {item.get('platform', '')}  "
                                        f"| 📅 {item.get('published_at', '')}"
                                    )
                                with c2:
                                    st.metric("相似度", f"{item.get('similarity', 0):.3f}")
                                st.caption(f"来源：{item.get('source', '')}")
                    else:
                        st.info("未找到相关结果")
                else:
                    st.error("搜索失败，请确认知识库服务可用")
            else:
                st.warning("请输入搜索关键词")

# ====================== 主路由 ======================
if not st.session_state.token:
    login_page()
else:
    with st.sidebar:
        st.markdown("## 🎬 AI 创作助手")
        st.markdown(f"👤 **{st.session_state.user}**")
        st.divider()

        # 导航（用 radio 保证单一选中）
        page = st.radio(
            "导航",
            ["🚀 工作台", "📋 方案浏览", "📜 历史记录", "📊 数据看板", "🔍 知识库搜索"],
            index=["🚀 工作台", "📋 方案浏览", "📜 历史记录", "📊 数据看板", "🔍 知识库搜索"].index(
                {"工作台": "🚀 工作台", "方案浏览": "📋 方案浏览", "历史记录": "📜 历史记录",
                 "数据看板": "📊 数据看板", "知识库搜索": "🔍 知识库搜索"}.get(
                    st.session_state.page, "🚀 工作台"
                )
            ) if st.session_state.page in {"工作台": "🚀 工作台", "方案浏览": "📋 方案浏览",
                "历史记录": "📜 历史记录", "数据看板": "📊 数据看板", "知识库搜索": "🔍 知识库搜索"} else 0,
            label_visibility="collapsed",
        )
        # 更新 page
        page_map = {"🚀 工作台": "工作台", "📋 方案浏览": "方案浏览", "📜 历史记录": "历史记录",
                     "📊 数据看板": "数据看板", "🔍 知识库搜索": "知识库搜索"}
        st.session_state.page = page_map[page]

        st.divider()
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # 页面路由
    routers = {
        "工作台": workbench_page, "方案浏览": schemes_page,
        "历史记录": history_page, "数据看板": dashboard_page,
        "知识库搜索": knowledge_page,
    }
    routers.get(st.session_state.page, workbench_page)()
