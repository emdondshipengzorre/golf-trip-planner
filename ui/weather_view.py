"""天气视图 — 目的地天气 + 高尔夫适宜度"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from scrapers.weather_scraper import get_weather_forecast


def render_weather_tab(city: str):
    """渲染天气 Tab"""

    st.header("🌤️ 目的地天气")

    forecast = get_weather_forecast(city)

    if not forecast:
        st.info(f"暂无{city}天气数据。请配置 OPENWEATHER_API_KEY 获取实时天气。")
        st.markdown("""
        **如何获取免费 API Key:**
        1. 访问 [openweathermap.org](https://openweathermap.org/api)
        2. 注册免费账号
        3. 复制 API Key 到 `.streamlit/secrets.toml`
        """)
        return

    # 概览
    today = forecast[0] if forecast else None
    if today:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("今日天气", today["weather"])
        col2.metric("温度", f"{today['temp']}°C",
                     delta=f"{today['temp_min']}~{today['temp_max']}°C")
        col3.metric("湿度", f"{today['humidity']}%")
        col4.metric("高尔夫适宜度", f"{today['golf_score']}/100",
                     delta="适合打球" if today["golf_score"] >= 70 else "条件一般",
                     delta_color="normal" if today["golf_score"] >= 70 else "inverse")

    # 温度趋势图
    st.subheader("📈 5日天气趋势")
    dates = [f["date"] for f in forecast]
    temps = [f["temp"] for f in forecast]
    temp_mins = [f["temp_min"] for f in forecast]
    temp_maxs = [f["temp_max"] for f in forecast]
    golf_scores = [f["golf_score"] for f in forecast]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=temp_maxs, mode="lines",
        name="最高温", line=dict(color="#E8453C", dash="dot"),
        fill=None,
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=temp_mins, mode="lines",
        name="最低温", line=dict(color="#2E86AB", dash="dot"),
        fill="tonexty", fillcolor="rgba(46,134,171,0.1)",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=temps, mode="lines+markers",
        name="平均温度", line=dict(color="#27AE60", width=3),
        marker=dict(size=8),
    ))

    fig.update_layout(
        xaxis_title="日期", yaxis_title="温度 (°C)",
        height=350, margin=dict(l=40, r=40, t=20, b=40),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 高尔夫适宜度
    st.subheader("⛳ 高尔夫适宜度")

    fig2 = go.Figure(go.Bar(
        x=dates, y=golf_scores,
        marker_color=[
            "#27AE60" if s >= 70 else "#F18F01" if s >= 50 else "#E8453C"
            for s in golf_scores
        ],
        text=[f"{s}分" for s in golf_scores],
        textposition="auto",
    ))
    fig2.update_layout(
        xaxis_title="日期", yaxis_title="适宜度",
        yaxis_range=[0, 100],
        height=300, margin=dict(l=40, r=40, t=20, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 每日详情
    st.subheader("📋 每日详情")
    for f in forecast:
        score = f["golf_score"]
        emoji = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
        st.markdown(
            f"{emoji} **{f['date']}** — {f['weather']} | "
            f"{f['temp_min']}~{f['temp_max']}°C | "
            f"湿度 {f['humidity']}% | 风速 {f['wind_speed']}m/s | "
            f"适宜度 {score}/100"
        )
