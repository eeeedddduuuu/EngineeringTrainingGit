"""
灵境智造 — AI 数字媒体创作引擎
前端 v4 · 多Agent协作 · 多平台适配
"""
import streamlit as st
import requests
import time
import json
import pandas as pd
import plotly.express as px
from pathlib import Path

# ====================== 配置 ======================
API = "http://127.0.0.1:8000/api"
API_BASE = API  # 兼容远程 P5 数据看板的变量名

st.set_page_config(page_title="灵境智造", page_icon="🔮", layout="wide")

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
        "token": None, "user": None, "page": "首页",
        "task_id": None, "task_status": None, "schemes": [],
        "provider": "deepseek",
        "img_analysis": "",
        "uploaded_img_url": "",
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
        st.markdown("""
        <div style="text-align:center; padding:40px 0 20px 0;">
            <div style="font-size:3rem; margin-bottom:8px;">🔮</div>
            <h1 style="font-size:2.2rem; margin:0; font-weight:800; letter-spacing:4px;">灵境智造</h1>
            <p style="font-size:0.85rem; opacity:0.5; margin-top:4px;">LINGJING ZHIZAO</p>
            <p style="font-size:0.9rem; opacity:0.6; margin-top:16px;">AI 驱动的数字媒体智能创作引擎</p>
        </div>
        """, unsafe_allow_html=True)

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

def _extract_version_md(full_md, version):
    """从完整 raw_markdown 中只提取指定版本的内容"""
    import re as _re
    if not full_md or not version:
        return full_md
    pattern = r'##\s*版本\s*' + version + r'\s*[：:]?(.*?)(?=\n##\s*(?:版本\s*[A-Ca-c]|推荐\s*|$))'
    m = _re.search(pattern, full_md, _re.DOTALL)
    if m:
        return m.group(1).strip()
    # 回退：按 ## 标题拆分
    parts = _re.split(r'\n(?=##\s*版本\s*)', full_md)
    idx = ord(version.upper()) - ord('A')
    if 0 <= idx < len(parts):
        return parts[idx]
    return full_md

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
                    full_md = s.get("raw_markdown") or (s.get("storyboard_json") or {}).get("raw_markdown", "")
                    version = s.get("version", "")
                    raw_md = _extract_version_md(full_md, version) if version and full_md else full_md
                    if scenes:
                        for sc in scenes:
                            vo = sc.get('voiceover', '')
                            st.markdown(
                                f"**{sc.get('seq')}.** [{sc.get('type','')}] "
                                f"`{sc.get('duration','')}` — {sc.get('description','')}"
                            )
                            if vo: st.caption(f"🎤 {vo[:200]}")
                    if raw_md:
                        st.caption("📝 完整脚本预览：")
                        st.text(raw_md[:5000])
                        if len(raw_md) > 5000:
                            st.caption(f"（共 {len(raw_md)} 字符，下载 Markdown 查看完整内容）")
                    if not scenes and not raw_md:
                        st.info("暂无详细脚本数据")
                    reason = s.get('recommendation_reason', '')
                    if reason:
                        st.markdown(f"💡 **推荐理由：** {reason}")
                    # 迭代建议（#15）
                    scores = s.get('scores') or (s.get('storyboard_json') or {}).get('scores', {})
                    if scores:
                        with st.expander("📈 评分详情与迭代建议"):
                            dims = [
                                ("开头钩子吸引力", "hook_score"),
                                ("结构与平台匹配度", "structure_score"),
                                ("目标受众匹配度", "audience_score"),
                                ("内容原创性", "originality_score"),
                                ("可执行性", "feasibility_score"),
                            ]
                            tips = {
                                "hook_score": "💡 尝试疑问句或反差制造悬念",
                                "structure_score": "💡 参考平台爆款模板调整节奏",
                                "audience_score": "💡 检查语言风格是否贴合目标受众",
                                "originality_score": "💡 寻找独特角度避免套路化",
                                "feasibility_score": "💡 简化场景降低拍摄难度",
                            }
                            for dim_name, dim_key in dims:
                                val = scores.get(dim_key, 5)
                                bar = "🟢" if val >= 7 else ("🟡" if val >= 5 else "🔴")
                                st.markdown(f"{bar} **{dim_name}：{val:.1f}**")
                                if val < 7:
                                    st.caption(f"  {tips.get(dim_key, '')}")

            if show_export and s.get("id"):
                dl1, dl2, dl3 = st.columns(3)
                with dl1:
                    r = api(f"/export/{s['id']}?format=md")
                    if r and r.status_code == 200:
                        st.download_button(
                            f"📥 MD", r.text, f"方案{s.get('version','')}.md",
                            mime="text/markdown", key=f"dl_{s.get('id','')}",
                            use_container_width=True,
                        )
                with dl2:
                    tts_text = s.get('hook', '')[:500] or s.get('title', '')[:200]
                    if st.button(f"🔊 配音", key=f"tts_{s.get('id','')}", use_container_width=True):
                        with st.spinner("🎙️ TTS 合成中..."):
                            tts_r = requests.post(f"{API}/creation/tts",
                                headers={"Authorization": f"Bearer {st.session_state.token}"},
                                data={"text": tts_text}, timeout=60)
                            if tts_r and tts_r.status_code == 200:
                                st.audio(tts_r.content, format="audio/mp3")
                            else:
                                st.error("TTS 失败")
                with dl3:
                    if st.button(f"🎬 视频", key=f"video_{s.get('id','')}", use_container_width=True,
                                 help="生成短视频样片（TTS配音+封面图+FFmpeg合成）"):
                        with st.spinner("🎬 生成短视频中（TTS→封面→FFmpeg）..."):
                            vid_r = requests.post(f"{API}/creation/render-video/{s['id']}",
                                headers={"Authorization": f"Bearer {st.session_state.token}"}, timeout=120)
                            if vid_r and vid_r.status_code == 200:
                                ct = vid_r.headers.get("content-type", "")
                                if "video" in ct:
                                    st.video(vid_r.content)
                                    st.download_button("📥 下载 MP4", vid_r.content,
                                        f"方案{s.get('version','')}.mp4", "video/mp4",
                                        key=f"vdl_{s.get('id','')}")
                                elif "audio" in ct:
                                    st.audio(vid_r.content, format="audio/mp3")
                                    st.info("FFmpeg 未安装，仅返回配音。安装 FFmpeg 后自动合成视频。")
                            else:
                                st.error("视频生成失败")

# ====================== 创作工作台 ======================
def workbench_page():
    st.title("🚀 创作工作台")
    st.caption("填写创作参数，AI Agent 流水线将自动生成 3 套差异化方案")

    # 参考素材区（表单外，上传后自动豆包分析）
    with st.container(border=True):
        st.caption("🖼️ 参考素材（可选）— 上传图片/视频/音频让 AI 更懂你的创作意图")
        up_col1, up_col2 = st.columns(2)
        with up_col1:
            uploaded = st.file_uploader("上传素材文件", type=["png", "jpg", "jpeg", "mp4", "mov", "mp3", "wav"], key="img_upload_v2")
        with up_col2:
            image_url = st.text_input("或粘贴图片链接", placeholder="https://example.com/image.jpg")

        # 上传后自动触发分析
        if uploaded and not st.session_state.get("img_analysis"):
            with st.spinner("🔍 豆包正在分析图片..."):
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                try:
                    ur = requests.post(f"{API}/creation/upload",
                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                        files=files, timeout=30)
                    if ur and ur.status_code == 200:
                        st.session_state.uploaded_img_url = ur.json().get("image_url", "")
                        ar = requests.post(f"{API}/creation/analyze-image",
                            headers={"Authorization": f"Bearer {st.session_state.token}"}, timeout=120)
                        if ar and ar.status_code == 200 and ar.json().get("ok"):
                            st.session_state.img_analysis = ar.json().get("analysis", "")
                            st.rerun()
                        else:
                            st.warning("图片分析未成功，但仍可用于创作")
                            st.session_state.img_analysis = "[图片已上传] 豆包分析中..."
                            st.rerun()
                except Exception as e:
                    st.warning(f"上传或分析失败: {e}")

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

                    img_url = st.session_state.get("uploaded_img_url", "") or ""

                    r = api("/creation/start", "POST", {
                        "topic": topic, "target_audience": audience or "通用",
                        "platform": pm[platform], "duration": dm[duration], "style": style,
                        "provider": st.session_state.provider,
                        "image_url": img_url or "",
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
        for i in range(60):
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

    # 图片分析结果显示
    if st.session_state.get("img_analysis", ""):
        with st.container(border=True):
            st.markdown("#### 🔍 豆包视觉分析结果")
            st.success(st.session_state.img_analysis)
            if st.button("✕ 清除分析结果", key="clear_img"):
                st.session_state.img_analysis = ""
                st.rerun()

    if not st.session_state.task_id:
        st.info("👆 填写主题和参数，点击「🔍 分析图片」预览AI理解，再点击「✨ 一键启动 AI 创作」生成脚本")

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

# ====================== 词云预生成（独立缓存 24h，与图表缓存解耦） ======================
@st.cache_data(ttl=86400, show_spinner=False)
def _get_wordclouds() -> list:
    """从 samples.xlsx 生成两张词云 PNG → base64。

    TTL=24h，独立于图表缓存。xlsx 数据是静态的，词云无需频繁重算。
    返回 [(title, base64_png), ...]，空列表表示无数据。
    """
    import base64, random, jieba
    from wordcloud import WordCloud
    from io import BytesIO

    samples_path = Path(__file__).resolve().parent.parent / "samples.xlsx"
    if not samples_path.exists():
        return []

    df = pd.read_excel(samples_path)
    C4 = ["#7c3aed", "#8b5cf6", "#a78bfa", "#c4b5fd"]
    stopwords = {"的","了","在","是","我","有","和","就","不","人","都","一","一个",
                 "上","也","很","到","说","要","去","你","会","着","没有","看","好",
                 "自己","这","他","她","它","们","那","及","与","或","等","为","以",
                 "将","对","把","被","从","让","但","而","且","所","如","之","其",
                 "可以","这个","那个","已经","还是","这些","那些","因为","所以","如果",
                 "虽然","然而","然后","之后","之前","可以","能够","需要","应该",
                 "通过","进行","使用","一种","每个","一些","许多","其他",
                 "中","更","较","最","非常","十分","特别","真正","完全","更加",
                 "还","再","又","才","只","便","即","却","仍","亦","尚","未","无","非"}
    jieba.setLogLevel(20)

    # 输出目录
    wc_dir = Path(__file__).resolve().parent / "static" / "wordclouds"
    wc_dir.mkdir(parents=True, exist_ok=True)

    result = []
    for wc_label, col_name, filename in [
        ("🏷️ 标题关键词云", "标题",    "wc_titles.png"),
        ("📝 内容摘要词云",   "内容摘要", "wc_summaries.png"),
    ]:
        if col_name not in df.columns:
            continue
        text = " ".join(df[col_name].dropna().astype(str).tolist())
        words = [w.strip() for w in jieba.cut(text)
                 if len(w.strip()) >= 2 and w.strip() not in stopwords]
        if not words:
            continue
        wc = WordCloud(
            width=600, height=380, background_color="white",
            font_path="C:/Windows/Fonts/msyh.ttc",
            color_func=lambda *a, **kw: random.choice(C4),
            max_words=80, collocations=False,
            margin=10, prefer_horizontal=0.75,
        )
        wc.generate(" ".join(words))
        buf = BytesIO()
        img = wc.to_image()
        img.save(buf, format="PNG")
        # 持久化到磁盘，供直接访问
        img.save(str(wc_dir / filename), format="PNG")
        result.append((wc_label, base64.b64encode(buf.getvalue()).decode()))

    return result


# ====================== 数据看板缓存构建器（预生成 .html 静态文件到 static/） ======================
@st.cache_data(ttl=3600, show_spinner="📊 正在生成统计图表…")
def _build_dashboard_html(total: int, topics_json: str, platforms_json: str, trends_json: str) -> str:
    """将 7 张 Plotly 图表预渲染为独立 .html + 合并版 dashboard_charts.html，缓存 1 小时。

    首次调用：生成图表 HTML → 写入 static/ → 返回完整 HTML。
    后续调用（同数据）：直接返回缓存，毫秒级响应。
    """
    topics   = json.loads(topics_json)
    platforms = json.loads(platforms_json)
    trends   = json.loads(trends_json)

    df_topic = pd.DataFrame(topics)
    plat_names = {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}
    df_plat = pd.DataFrame(platforms)
    df_plat["name"] = df_plat["platform"].map(plat_names).fillna(df_plat["platform"])
    df_trend = pd.DataFrame(trends) if trends else pd.DataFrame()

    # ── 纯紫系 4 阶配色（无绿无黑）──
    C = {
        "p4": "#7c3aed", "p3": "#8b5cf6", "p2": "#a78bfa", "p1": "#c4b5fd",
        "bg": "#f5f3ff", "slate": "#64748b", "dark": "#1e293b", "white": "#ffffff",
        "p_colors": ["#7c3aed", "#8b5cf6", "#a78bfa", "#c4b5fd"],
    }

    # ── 静态文件输出目录 ──
    static_dir = Path(__file__).resolve().parent / "static"
    charts_dir = static_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    # ── 共享 Plotly 布局 ──
    def _layout(title, h=400, **kw):
        return dict(
            title=dict(text=title, font=dict(size=16, color=C["dark"]), x=0),
            height=h, margin=dict(t=44, b=0, l=0, r=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_family="Microsoft YaHei", **kw
        )

    # ────────────── ① 主题环形图 ──────────────
    fig1 = px.pie(df_topic, values="count", names="name", hole=0.55,
                  color_discrete_sequence=C["p_colors"])
    fig1.update_traces(textposition="inside", textinfo="percent",
                       textfont=dict(size=14, color="white", family="Microsoft YaHei"),
                       marker=dict(line=dict(color="white", width=2)))
    fig1.update_layout(**_layout("① 主题分布 · 环形图"),
                        legend=dict(orientation="h", y=-0.12, font=dict(size=12, color=C["slate"])))

    # ────────────── ② 平台柱状图 ──────────────
    pc = C["p_colors"][:len(df_plat)]
    fig2 = px.bar(df_plat, x="name", y="count", color_discrete_sequence=pc)
    fig2.update_traces(marker=dict(color=pc, line=dict(width=0)),
                       text=df_plat["count"], textposition="outside",
                       textfont=dict(size=15, color=C["slate"], family="Microsoft YaHei"), width=0.5)
    fig2.update_layout(**_layout("② 平台分布 · 柱状图"),
                        xaxis=dict(title="", tickfont=dict(size=13, color=C["dark"], family="Microsoft YaHei"), showgrid=False),
                        yaxis=dict(title="", showticklabels=False, showgrid=False), showlegend=False)

    # ────────────── ③ 月度趋势面积图 ──────────────
    fig3 = px.area(df_trend, x="month", y="count")
    fig3.update_traces(line=dict(color=C["p4"], width=2), fillcolor="rgba(124,58,237,0.10)",
                       marker=dict(size=4, color=C["p4"], line=dict(width=2, color="white")))
    fig3.update_layout(**_layout("③ 月度趋势 · 面积图", h=360),
                        xaxis=dict(title=dict(text="月份", font=dict(size=12, color=C["slate"])),
                                   tickfont=dict(size=11, color=C["slate"]), tickangle=-45,
                                   showgrid=False, tickmode="linear", dtick=2,
                                   showline=True, linecolor="#e2e8f0", linewidth=1),
                        yaxis=dict(title=dict(text="数量", font=dict(size=12, color=C["slate"])),
                                   showgrid=True, gridcolor="#f1f5f9", tickfont=dict(size=11, color=C["slate"]),
                                   showline=True, linecolor="#e2e8f0", linewidth=1))

    # ────────────── ④ 词云（独立缓存 24h，首次生成后秒读）──
    wc_images = _get_wordclouds()  # [(label, base64_png), ...]

    # ────────────── ⑤ 类别对比横向柱状图 ──────────────
    df_sorted = df_topic.sort_values("count", ascending=True)
    fig5 = px.bar(df_sorted, y="name", x="count", orientation="h")
    g5 = C["p_colors"][:len(df_sorted)]
    fig5.update_traces(marker=dict(color=g5, line=dict(width=0)),
                       text=df_sorted["count"], textposition="outside",
                       textfont=dict(size=15, color=C["slate"], family="Microsoft YaHei"), width=0.55)
    fig5.update_layout(**_layout("⑤ 类别对比 · 横向柱状图"),
                        xaxis=dict(title="", showgrid=False, showticklabels=False),
                        yaxis=dict(title="", tickfont=dict(size=13, color=C["dark"], family="Microsoft YaHei")),
                        showlegend=False)

    # ────────────── ⑥ 主题树图 ──────────────
    fig6 = px.treemap(df_topic, path=["name"], values="count", color="count",
                      color_continuous_scale=[(0, C["p1"]), (0.5, C["p2"]), (1, C["p4"])])
    fig6.update_traces(textinfo="label+value",
                       textfont=dict(size=16, color="white", family="Microsoft YaHei"),
                       hovertemplate="<b>%{{label}}</b><br>数量: %{{value}}<extra></extra>")
    fig6.update_layout(**_layout("⑥ 主题分布 · 树图"))

    # ────────────── ⑦ 平台占比饼图 ──────────────
    fig7 = px.pie(df_plat, values="count", names="name",
                  color_discrete_sequence=C["p_colors"][:len(df_plat)])
    fig7.update_traces(textposition="inside", textinfo="percent+label",
                       textfont=dict(size=14, color="white", family="Microsoft YaHei"),
                       marker=dict(line=dict(color="white", width=2)))
    fig7.update_layout(**_layout("⑦ 平台占比 · 饼图"), showlegend=False)

    all_figs = [
        ("chart_1_donut",          fig1),
        ("chart_2_bar",            fig2),
        ("chart_3_area",           fig3),
        ("chart_4_hbar",           fig5),
        ("chart_5_treemap",        fig6),
        ("chart_6_pie",            fig7),
    ]

    # ── 写入独立 .html 文件（每个图表一个完整页面，CDN 加载 Plotly.js）──
    for name, fig in all_figs:
        fig.write_html(
            str(charts_dir / f"{name}.html"),
            include_plotlyjs="cdn",
            full_html=True,
            config={"responsive": True, "displayModeBar": False},
        )

    # ── 组装合并版 HTML 片段（清除固定宽度 → 完全响应式）──
    import re
    chart_snippets = []
    for name, fig in all_figs:
        # 从根本上清除 figure 的固定宽度，让 Plotly.js responsive 接管
        fig.layout.pop("width", None)
        snippet = fig.to_html(include_plotlyjs=False, full_html=False,
                              config={"responsive": True, "displayModeBar": False})
        # div style: width:700px → width:100%
        snippet = re.sub(r'width:\s*\d+px', 'width:100%', snippet)
        chart_snippets.append(snippet)

    # ── 月度明细表 HTML ──
    table_html = ""
    if not df_trend.empty:
        dm = df_trend.tail(12).sort_values("month", ascending=False).copy()
        dm.columns = ["月份", "数量"]
        dm["环比"] = dm["数量"].diff(-1).fillna(0).astype(int)
        dm["环比"] = dm["环比"].apply(lambda x: f"+{x}" if x > 0 else str(x) if x < 0 else "—")
        rows = []
        for _, row in dm.iterrows():
            bg = C["bg"] if row["月份"].startswith("2026") else "transparent"
            rows.append(f"""<tr style="background:{bg};">
              <td style="padding:8px 12px;color:{C['dark']};font-weight:500">{row['月份']}</td>
              <td style="padding:8px 12px;color:{C['dark']};text-align:right">{int(row['数量'])} 条</td>
              <td style="padding:8px 12px;color:{C['slate']};text-align:right;font-size:12px">{row['环比']}</td>
            </tr>""")
        table_html = f"""
        <div class="tbl-card">
          <div class="tbl-title">📋 最近 12 个月明细</div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            {"".join(rows)}
          </table>
        </div>"""

    # ── 合并版完整 HTML 文档 ──
    combined = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>数据看板</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Microsoft YaHei','PingFang SC',sans-serif; background:#f8f9fb; padding:24px 28px; color:{C['dark']}; }}
  .header {{ display:flex; align-items:baseline; gap:16px; margin-bottom:24px; }}
  .header h1 {{ font-size:22px; font-weight:700; }}
  .header span {{ font-size:13px; color:{C['slate']}; }}
  .kpi-row {{ display:flex; gap:16px; margin-bottom:20px; }}
  .kpi {{ flex:1; background:#fff; border-radius:14px; padding:22px 16px; text-align:center;
          border:1px solid #eef2ff; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
  .kpi .label {{ font-size:12px; color:{C['slate']}; margin-bottom:6px; letter-spacing:.5px; }}
  .kpi .value {{ font-size:30px; font-weight:700; }}
  .kpi .unit {{ font-size:13px; font-weight:400; color:{C['slate']}; margin-left:4px; }}
  .row {{ display:flex; gap:16px; margin-bottom:16px; }}
  .card {{ flex:1; min-width:0; background:#fff; border-radius:14px; padding:14px;
          border:1px solid #eef2ff; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
  .card .plotly-graph-div {{ width:100% !important; max-width:100%; }}
  .full {{ background:#fff; border-radius:14px; padding:14px; margin-bottom:16px;
          border:1px solid #eef2ff; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
  .full .plotly-graph-div {{ width:100% !important; max-width:100%; }}
  .tbl-card {{ background:#fff; border-radius:14px; padding:18px 20px; flex:1;
              border:1px solid #eef2ff; box-shadow:0 1px 3px rgba(0,0,0,.04); overflow:auto; }}
  .tbl-title {{ font-size:15px; font-weight:700; color:{C['dark']}; margin-bottom:14px; }}
  .footer {{ text-align:center; color:{C['slate']}; font-size:12px; padding:12px 0 4px; }}
</style></head>
<body>
<div class="header">
  <h1>📊 样例数据统计</h1>
  <span>samples.xlsx · {total} 条 · {len(trends)} 个月</span>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="label">样例总数</div><div class="value">{total}<span class="unit">条</span></div></div>
  <div class="kpi"><div class="label">主题类别</div><div class="value">{len(topics)}<span class="unit">类</span></div></div>
  <div class="kpi"><div class="label">覆盖平台</div><div class="value">{len(platforms)}<span class="unit">个</span></div></div>
  <div class="kpi"><div class="label">时间跨度</div><div class="value">{len(trends)}<span class="unit">月</span></div></div>
</div>

<div class="row">
  <div class="card">{chart_snippets[0]}</div>
  <div class="card">{chart_snippets[1]}</div>
</div>

<div class="full">{chart_snippets[2]}</div>

<div class="row">
  {f'''<div class="card" style="text-align:center">
    <div style="font-size:15px;font-weight:700;color:{C['dark']};margin-bottom:12px">{wc_images[0][0]}</div>
    <img src="data:image/png;base64,{wc_images[0][1]}" style="width:100%;border-radius:8px" alt="标题词云">
  </div>
  <div class="card" style="text-align:center">
    <div style="font-size:15px;font-weight:700;color:{C['dark']};margin-bottom:12px">{wc_images[1][0]}</div>
    <img src="data:image/png;base64,{wc_images[1][1]}" style="width:100%;border-radius:8px" alt="内容词云">
  </div>''' if len(wc_images) >= 2 else ''}
</div>

<div class="row">
  <div class="card">{chart_snippets[3]}</div>
  <div class="card">{chart_snippets[4]}</div>
</div>

<div class="row">
  <div class="card">{chart_snippets[5]}</div>
  {table_html}
</div>

<div class="footer">P5 数据/知识库模块 · samples.xlsx（{total} 条）· 6 图表 + 2 词云 + 4 指标卡 · 静态预渲染</div>
<script>
// 所有图表渲染完成后强制 resize 使其适配容器宽度
(function(){{
  var divs = document.querySelectorAll('.plotly-graph-div');
  divs.forEach(function(el){{ try{{ Plotly.Plots.resize(el); }}catch(e){{}} }});
}})();
</script>
</body></html>"""

    # 持久化合并版
    (static_dir / "dashboard_charts.html").write_text(combined, encoding="utf-8")

    return combined


# ====================== 数据看板页面 ======================
def dashboard_page():
    """加载数据 → 交给缓存构建器生成 HTML → iframe 渲染（二次进入秒开）"""
    r = api("/stats/samples")
    if not r or r.status_code != 200:
        st.warning("无法获取统计数据"); return
    d = r.json()

    total = d.get("total_samples", 0)
    if total == 0:
        st.warning("暂无数据"); return

    html = _build_dashboard_html(
        total,
        json.dumps(d.get("topic_distribution", [])),
        json.dumps(d.get("platform_distribution", [])),
        json.dumps(d.get("monthly_trends", [])),
    )
    st.components.v1.html(html, height=2900, scrolling=True)

# ====================== 知识库搜索 ======================
def knowledge_page():
    st.title("🔍 知识库搜索")
    st.caption("语义检索 50 条样例数据，查看相似内容和引用来源")

    # 初始化 session_state 持久化存储
    if "kb_results" not in st.session_state:
        st.session_state.kb_results = None
    if "kb_query" not in st.session_state:
        st.session_state.kb_query = ""
    if "kb_error" not in st.session_state:
        st.session_state.kb_error = None

    with st.container(border=True):
        q = st.text_input("搜索关键词", placeholder="例：短视频脚本、游戏剧情、品牌宣传")
        top = st.slider("返回条数", 1, 20, 5)
        if st.button("🔍 搜索", use_container_width=True, type="primary"):
            if not q.strip():
                st.warning("请输入搜索关键词")
            else:
                with st.spinner("正在检索..."):
                    # 使用 params dict 传递查询参数，确保中文字符正确 URL 编码
                    r = api("/knowledge/search", "GET", {"q": q.strip(), "top_k": top})
                if r is None:
                    st.session_state.kb_error = "❌ 无法连接后端服务，请确认服务已启动 (http://127.0.0.1:8000)"
                    st.session_state.kb_results = None
                    st.session_state.kb_query = ""
                elif r.status_code == 200:
                    results = r.json().get("results", [])
                    st.session_state.kb_results = results
                    st.session_state.kb_query = q.strip()
                    st.session_state.kb_error = None
                elif r.status_code == 401:
                    st.session_state.kb_error = "❌ 登录已过期，请重新登录"
                    st.session_state.kb_results = None
                    st.session_state.kb_query = ""
                elif r.status_code == 503:
                    st.session_state.kb_error = "❌ 知识库服务暂不可用，请检查 chromadb 和 Embedding 模型是否正确安装"
                    st.session_state.kb_results = None
                    st.session_state.kb_query = ""
                else:
                    try:
                        detail = r.json().get("detail", r.text[:200])
                    except Exception:
                        detail = r.text[:200]
                    st.session_state.kb_error = f"❌ 搜索失败 (HTTP {r.status_code}): {detail}"
                    st.session_state.kb_results = None
                    st.session_state.kb_query = ""

    # ── 持久化展示搜索结果（不依赖 st.button 的瞬时状态）──
    if st.session_state.kb_error:
        st.error(st.session_state.kb_error)

    if st.session_state.kb_results is not None:
        results = st.session_state.kb_results
        if results:
            st.success(f"🔍 「{st.session_state.kb_query}」— 找到 {len(results)} 条结果")
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
            st.info(f"🔍 「{st.session_state.kb_query}」— 未找到相关结果，请尝试其他关键词")

# ====================== 首页 ======================
def home_page():
    # Hero 区
    st.markdown("""
    <div style="text-align:center; padding:60px 0 36px 0;">
        <div style="font-size:5rem; margin-bottom:16px; line-height:1;">🔮</div>
        <h1 style="font-size:2.6rem; margin:0; font-weight:800; letter-spacing:8px;">灵境智造</h1>
        <p style="font-size:0.75rem; opacity:0.35; margin:4px 0 0 0; letter-spacing:4px;">LINGJING ZHIZAO</p>
    </div>
    """, unsafe_allow_html=True)

    # CTA 按钮
    _, cc, _ = st.columns([1, 1, 1])
    with cc:
        if st.button("✨ 开始创作", use_container_width=True, type="primary"):
            st.session_state.page = "工作台"; st.rerun()

    st.divider()

    # 功能介绍卡片
    st.markdown("### 平台能力")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown("""
        <div style="text-align:center; padding:20px 12px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <div style="font-size:1.6rem;">🧠</div>
            <h4 style="margin:8px 0 4px 0;">多 Agent 协作</h4>
            <p style="font-size:0.75rem; opacity:0.5; margin:0;">趋势分析 · 脚本创作<br>合规审查 · 发布策略</p>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div style="text-align:center; padding:20px 12px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <div style="font-size:1.6rem;">📱</div>
            <h4 style="margin:8px 0 4px 0;">多平台适配</h4>
            <p style="font-size:0.75rem; opacity:0.5; margin:0;">抖音 · 小红书 · B站<br>不同平台不同风格</p>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div style="text-align:center; padding:20px 12px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <div style="font-size:1.6rem;">📋</div>
            <h4 style="margin:8px 0 4px 0;">3 方案对比</h4>
            <p style="font-size:0.75rem; opacity:0.5; margin:0;">多版本脚本 · A/B 对比<br>智能评分推荐</p>
        </div>
        """, unsafe_allow_html=True)
    with f4:
        st.markdown("""
        <div style="text-align:center; padding:20px 12px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <div style="font-size:1.6rem;">📦</div>
            <h4 style="margin:8px 0 4px 0;">一键导出</h4>
            <p style="font-size:0.75rem; opacity:0.5; margin:0;">Markdown · Word<br>分镜表 · 素材清单</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 使用引导
    st.markdown("### 使用指引")
    guide_html = """
    <div style="display:flex; gap:16px;">
        <div style="flex:1; padding:20px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <span style="display:inline-block; width:26px; height:26px; line-height:26px; text-align:center; border-radius:50%; background:rgba(99,102,241,0.2); color:#818cf8; font-weight:700; font-size:0.8rem; margin-right:8px;">1</span>
            <span style="font-weight:600;">输入创作需求</span>
            <p style="font-size:0.8rem; opacity:0.5; margin:6px 0 0 34px;">填写主题、目标受众、发布平台、时长和风格偏好</p>
        </div>
    </div>
    <div style="margin-top:12px;">
        <div style="flex:1; padding:20px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <span style="display:inline-block; width:26px; height:26px; line-height:26px; text-align:center; border-radius:50%; background:rgba(99,102,241,0.2); color:#818cf8; font-weight:700; font-size:0.8rem; margin-right:8px;">2</span>
            <span style="font-weight:600;">AI 流水线自动创作</span>
            <p style="font-size:0.8rem; opacity:0.5; margin:6px 0 0 34px;">4 个 Agent 协作：热点分析 → 脚本创作 → 合规审查 → 发布策略，生成 3 套完整方案</p>
        </div>
    </div>
    <div style="margin-top:12px;">
        <div style="flex:1; padding:20px; border-radius:10px; border:1px solid rgba(128,128,128,0.08);">
            <span style="display:inline-block; width:26px; height:26px; line-height:26px; text-align:center; border-radius:50%; background:rgba(99,102,241,0.2); color:#818cf8; font-weight:700; font-size:0.8rem; margin-right:8px;">3</span>
            <span style="font-weight:600;">对比选择 + 导出</span>
            <p style="font-size:0.8rem; opacity:0.5; margin:6px 0 0 34px;">A/B 方案对比，选择最佳方案，一键导出 Markdown 或 Word</p>
        </div>
    </div>
    """
    st.markdown(guide_html, unsafe_allow_html=True)

# ====================== 审核看板页（#17） ======================
def review_page():
    st.title("✅ 审核看板")
    st.caption("在线审核方案 · 通过/拒绝 · 审核意见")

    r = api("/history?page=1&size=50")
    if not r or r.status_code != 200: st.error("无法加载"); return
    items = r.json().get("items", [])
    sessions = [it for it in items if it.get("scheme_count", 0) > 0]
    if not sessions: st.info("暂无方案可审核"); return

    sel = st.selectbox("选择会话", [it["session_id"] for it in sessions],
        format_func=lambda x: f"#{x} — {next((i['topic'] for i in sessions if i['session_id'] == x), '')}")

    if st.button("加载方案", use_container_width=True, type="primary"):
        r2 = api(f"/schemes?session_id={sel}")
        if r2 and r2.status_code == 200:
            schemes = r2.json().get("schemes", [])
            status_map = {"approved": "✅ 已通过", "rejected": "❌ 已拒绝", "review": "💬 需修改"}
            for s in schemes:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 1])
                    with c1: st.markdown(f"**方案 {s['version']}** — {s.get('title', '')[:50]}")
                    with c2: st.markdown(f"⭐ {s.get('score', 0)}")
                    with c3:
                        if st.button("✅ 通过", key=f"approve_{s['id']}", use_container_width=True):
                            r3 = api("/review", "POST", {"scheme_id": s["id"], "status": "approved", "comment": "审核通过"})
                            if r3 and r3.status_code == 200: st.success("已通过"); st.rerun()
                    with c4:
                        if st.button("❌ 拒绝", key=f"reject_{s['id']}", use_container_width=True):
                            r3 = api("/review", "POST", {"scheme_id": s["id"], "status": "rejected", "comment": "需修改后重新提交"})
                            if r3 and r3.status_code == 200: st.warning("已拒绝"); st.rerun()
                    with c5:
                        comment = st.text_input("意见", key=f"comment_{s['id']}", placeholder="审核意见...")
                        if comment and st.button("💬", key=f"submit_{s['id']}"):
                            r3 = api("/review", "POST", {"scheme_id": s["id"], "status": "review", "comment": comment})
                            if r3 and r3.status_code == 200: st.success("已提交")
                    st.caption(f"状态：{status_map.get(s.get('review_status', ''), '⏳ 待审核')}")

# ====================== 主路由 ======================
if not st.session_state.token:
    login_page()
else:
    with st.sidebar:
        st.markdown("## 🔮 灵境智造")
        st.markdown(f"👤 **{st.session_state.user}**")
        st.divider()

        # AI 模式切换
        st.caption("🤖 AI 引擎")
        provider_labels = {"mock": "⚡ Mock 离线（秒出）", "deepseek": "🧠 DeepSeek v4（真实AI）", "coze": "🔗 Coze 扣子（平台）"}
        pidx = list(provider_labels.keys()).index(st.session_state.provider) if st.session_state.provider in provider_labels else 0
        selected = st.selectbox("AI引擎", list(provider_labels.values()), index=pidx, label_visibility="collapsed")
        st.session_state.provider = {v: k for k, v in provider_labels.items()}[selected]
        st.caption(f"当前：{selected}")
        st.divider()

        # 导航（用 radio 保证单一选中）
        page = st.radio(
            "导航",
            ["🏠 首页", "🚀 工作台", "📋 方案浏览", "📜 历史记录", "📊 数据看板", "🔍 知识库搜索", "✅ 审核看板"],
            index=["🏠 首页", "🚀 工作台", "📋 方案浏览", "📜 历史记录", "📊 数据看板", "🔍 知识库搜索", "✅ 审核看板"].index(
                {"首页": "🏠 首页", "工作台": "🚀 工作台", "方案浏览": "📋 方案浏览",
                 "历史记录": "📜 历史记录", "数据看板": "📊 数据看板", "知识库搜索": "🔍 知识库搜索", "审核看板": "✅ 审核看板"}.get(
                    st.session_state.page, "🏠 首页"
                )
            ) if st.session_state.page in {"首页": "🏠 首页", "工作台": "🚀 工作台", "方案浏览": "📋 方案浏览",
                "历史记录": "📜 历史记录", "数据看板": "📊 数据看板", "知识库搜索": "🔍 知识库搜索", "审核看板": "✅ 审核看板"} else 0,
            label_visibility="collapsed",
        )
        # 更新 page
        page_map = {"🏠 首页": "首页", "🚀 工作台": "工作台", "📋 方案浏览": "方案浏览",
                     "📜 历史记录": "历史记录", "📊 数据看板": "数据看板", "🔍 知识库搜索": "知识库搜索",
                     "✅ 审核看板": "审核看板"}
        st.session_state.page = page_map[page]

        st.divider()
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # 页面路由
    routers = {
        "首页": home_page, "工作台": workbench_page,
        "方案浏览": schemes_page, "历史记录": history_page, "审核看板": review_page,
        "数据看板": dashboard_page, "知识库搜索": knowledge_page,
    }
    routers.get(st.session_state.page, home_page)()
