"""数据看板页面 — P5 统计可视化"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from frontend.utils.api import api_get

st.set_page_config(page_title="数据看板", page_icon="📊", layout="wide")

st.title("📊 样例数据看板")

# ── 加载数据 ──
try:
    data = api_get("/stats/samples")
except Exception as e:
    st.error(f"无法加载统计数据: {e}")
    st.stop()

total = data.get("total_samples", 0)
topics = data.get("topic_distribution", [])
platforms = data.get("platform_distribution", [])
trends = data.get("monthly_trends", [])

if total == 0:
    st.warning("暂无统计数据")
    st.stop()

# ── 1. 顶部指标卡 ──
st.markdown("### 📈 核心指标")
cols = st.columns(4)
with cols[0]:
    st.metric("📦 样例总数", f"{total} 条")
with cols[1]:
    st.metric("🏷️ 类别数", f"{len(topics)} 类")
with cols[2]:
    st.metric("📱 平台数", f"{len(platforms)} 个")
with cols[3]:
    avg_per_cat = total // len(topics) if topics else 0
    st.metric("📊 每类平均", f"{avg_per_cat} 条")

st.divider()

# ── 2. 图表区：第一行 ──
st.markdown("### 🎨 数据可视化")
row1_left, row1_right = st.columns(2)

# 主题分布 — 饼图
with row1_left:
    st.subheader("样例主题分布")
    df_topic = pd.DataFrame(topics)
    colors = ["#4ECDC4", "#FF6B6B", "#FFE66D", "#95E1D3", "#F38181", "#AA96DA"]
    fig = px.pie(
        df_topic, values="count", names="name",
        color_discrete_sequence=colors,
        hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

# 平台分布 — 柱状图
with row1_right:
    st.subheader("平台分布")
    df_platform = pd.DataFrame(platforms)
    # 平台名映射为中文
    platform_names = {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}
    df_platform["平台名"] = df_platform["platform"].map(platform_names).fillna(df_platform["platform"])
    colors_bar = ["#FF6B6B", "#4ECDC4", "#FFE66D"]
    fig = px.bar(
        df_platform, x="平台名", y="count",
        color="平台名", color_discrete_sequence=colors_bar,
        text="count",
    )
    fig.update_traces(textposition="outside", textfont_size=14)
    fig.update_layout(
        height=400,
        xaxis_title="", yaxis_title="样例数量",
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 3. 图表区：第二行 ──
st.markdown("### 📅 趋势与对比")
row2_left, row2_right = st.columns(2)

# 月度趋势 — 面积折线图
with row2_left:
    st.subheader("月度发布趋势")
    if trends:
        df_trends = pd.DataFrame(trends)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trends["month"], y=df_trends["count"],
            mode="lines+markers",
            line=dict(color="#FF6B6B", width=3),
            fill="tozeroy",
            fillcolor="rgba(255,107,107,0.15)",
            marker=dict(size=8, color="#FF6B6B", line=dict(width=2, color="white")),
        ))
        fig.update_layout(
            height=400,
            xaxis_title="", yaxis_title="样例数量",
            margin=dict(t=10, b=10, l=10, r=10),
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无趋势数据")

# 主题分布 — 横向柱状图
with row2_right:
    st.subheader("类别数量对比")
    df_sorted = df_topic.sort_values("count", ascending=True)
    colors_h = ["#4ECDC4", "#FF6B6B", "#FFE66D", "#95E1D3", "#F38181", "#AA96DA"]
    fig = px.bar(
        df_sorted, y="name", x="count",
        orientation="h",
        color="name", color_discrete_sequence=colors_h,
        text="count",
    )
    fig.update_traces(textposition="outside", textfont_size=14)
    fig.update_layout(
        height=400,
        xaxis_title="样例数量", yaxis_title="",
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 4. 图表区：第三行 ──
st.markdown("### 🔍 多维度分析")
row3_left, row3_right = st.columns(2)

# 类别占比环形图
with row3_left:
    st.subheader("类别占比（环形）")
    fig = px.pie(
        df_topic, values="count", names="name",
        color_discrete_sequence=colors,
        hole=0.6,
    )
    fig.update_traces(
        textposition="outside", textinfo="percent+label",
        pull=[0.05] * len(df_topic),
    )
    fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=60),
    )
    fig.add_annotation(
        text=f"总计<br>{total}条", x=0.5, y=0.5,
        font_size=20, showarrow=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# 平台占比 — 水平堆叠
with row3_right:
    st.subheader("各平台内容供给")
    # 创建热力矩阵模拟（每个类别在平台的分布）
    heatmap_data = []
    for t in topics:
        # 按比例分配（简化模拟）
        name = t["name"]
        count = t["count"]
        for p in platforms:
            pname = platform_names.get(p["platform"], p["platform"])
            # 按平台总量比例分配
            ratio = p["count"] / total
            heatmap_data.append({
                "类别": name,
                "平台": pname,
                "数量": round(count * ratio, 1),
            })
    df_heat = pd.DataFrame(heatmap_data)
    fig = px.treemap(
        df_heat, path=["类别", "平台"], values="数量",
        color="数量", color_continuous_scale=["#95E1D3", "#4ECDC4", "#FF6B6B"],
    )
    fig.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 5. 底部：月度趋势表 ──
st.markdown("### 📋 月度明细")
if trends:
    df_monthly = pd.DataFrame(trends)
    df_monthly.columns = ["月份", "样例数"]
    df_monthly["环比增长"] = df_monthly["样例数"].diff().fillna(0).astype(int)
    df_monthly["环比增长率"] = (df_monthly["样例数"].pct_change() * 100).fillna(0).round(1).astype(str) + "%"
    st.dataframe(
        df_monthly.tail(12).sort_values("月份", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("暂无月度数据")

st.caption(f"数据来源: samples.xlsx（{total} 条样例）| P5 数据/知识库模块")
