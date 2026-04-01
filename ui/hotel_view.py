"""酒店推荐视图"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.hotel_recommender import recommend_hotels


def render_hotel_tab(
    city: str, checkin: str, checkout: str,
    course_lat: float = None, course_lng: float = None,
    budget_max: int = None, hotel_type: str = None,
):
    """渲染酒店推荐 Tab"""

    st.header("🏨 酒店推荐")

    with st.spinner("正在搜索酒店..."):
        data = recommend_hotels(city, checkin, checkout, course_lat, course_lng, budget_max, hotel_type)

    filtered = data["filtered"]

    if not filtered:
        st.warning("当前筛选条件下没有找到酒店，试试调整预算或偏好")
        filtered = data["all_hotels"]
        if not filtered:
            return

    # 指标卡
    col1, col2, col3 = st.columns(3)
    if data["best_value"]:
        col1.metric("🏆 性价比之选", data["best_value"]["name"],
                     delta=f"¥{data['best_value']['price_per_night']}/晚")
    if data["nearest"]:
        col2.metric("📍 离球场最近", data["nearest"]["name"],
                     delta=f"{data['nearest']['distance_to_course_km']}km")
    if data["cheapest"]:
        col3.metric("💰 最实惠", data["cheapest"]["name"],
                     delta=f"¥{data['cheapest']['price_per_night']}/晚")

    # 性价比散点图
    st.subheader("💎 价格 vs 评分")
    fig = go.Figure()
    for h in filtered:
        fig.add_trace(go.Scatter(
            x=[h["price_per_night"]], y=[h["rating"]],
            mode="markers+text",
            marker=dict(
                size=h["value_score"] * 2,
                color={"豪华": "#E8453C", "舒适": "#2E86AB", "经济": "#27AE60"}.get(h["type"], "#888"),
            ),
            text=[h["name"]], textposition="top center",
            name=h["name"],
            hovertemplate=f"<b>{h['name']}</b><br>¥{h['price_per_night']}/晚<br>评分: {h['rating']}<br>距球场: {h.get('distance_to_course_km', '未知')}km",
        ))

    fig.update_layout(
        xaxis_title="每晚价格 (¥)", yaxis_title="评分",
        height=400, margin=dict(l=40, r=40, t=40, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 酒店列表
    st.subheader("📋 酒店列表")
    df = pd.DataFrame([{
        "酒店": h["name"],
        "类型": h["type"],
        "价格/晚": f"¥{h['price_per_night']}",
        "评分": f"⭐ {h['rating']}",
        "距球场": f"{h['distance_to_course_km']}km" if h.get("distance_to_course_km") else "—",
        "车程": f"{h['drive_minutes']}分钟" if h.get("drive_minutes") else "—",
        "性价比": f"{h['value_score']:.1f}",
        "来源": h.get("source", "—"),
    } for h in filtered])
    st.dataframe(df, use_container_width=True, hide_index=True)
