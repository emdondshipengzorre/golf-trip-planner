"""机票比价视图"""

import plotly.graph_objects as go
import streamlit as st

from core.flight_analyzer import analyze_price_trend, compare_flights


def render_flight_tab(origin: str, destination: str, date: str, trend_days: int = 30):
    """渲染机票比价 Tab"""

    st.header("✈️ 机票比价")

    # 价格走势
    with st.spinner("正在分析价格走势..."):
        trend = analyze_price_trend(origin, destination, date, trend_days)

    if trend["best_date"]:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最低价", f"¥{trend['best_price']}")
        col2.metric("最佳日期", trend["best_date"])
        col3.metric("工作日均价", f"¥{trend['weekday_avg']}")
        col4.metric("周末均价", f"¥{trend['weekend_avg']}",
                     delta=f"+¥{trend['weekend_avg'] - trend['weekday_avg']}", delta_color="inverse")

    # 价格走势图
    st.subheader("📈 价格走势")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["dates"], y=trend["min_prices"],
        mode="lines+markers", name="最低价",
        line=dict(color="#2E86AB", width=2),
        marker=dict(size=4),
    ))

    if trend["best_date"]:
        fig.add_trace(go.Scatter(
            x=[trend["best_date"]], y=[trend["best_price"]],
            mode="markers+text", name="最低价日期",
            marker=dict(size=12, color="#E8453C", symbol="star"),
            text=[f"¥{trend['best_price']}"],
            textposition="top center",
        ))

    fig.update_layout(
        xaxis_title="日期", yaxis_title="价格 (¥)",
        height=400, margin=dict(l=40, r=40, t=40, b=40),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 当日航班对比
    st.subheader("📊 航班对比")
    with st.spinner("正在查询航班..."):
        comparison = compare_flights(origin, destination, date)

    if comparison["flights"]:
        flights = comparison["flights"]

        # 航司柱状图
        airlines = list(comparison["by_airline"].keys())
        avg_prices = [
            round(sum(f["price"] for f in fs) / len(fs))
            for fs in comparison["by_airline"].values()
        ]
        fig2 = go.Figure(go.Bar(
            x=airlines, y=avg_prices,
            marker_color=["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B"][:len(airlines)],
            text=[f"¥{p}" for p in avg_prices], textposition="auto",
        ))
        fig2.update_layout(
            xaxis_title="航空公司", yaxis_title="均价 (¥)",
            height=300, margin=dict(l=40, r=40, t=20, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)

        # 航班列表
        import pandas as pd
        df = pd.DataFrame([{
            "航班号": f["flight_no"],
            "航司": f["airline"],
            "出发": f["dep_time"],
            "到达": f["arr_time"],
            "时长": f["duration"],
            "价格": f"¥{f['price']}",
            "红眼": "🌙" if f["is_red_eye"] else "",
            "来源": f.get("source", "—"),
        } for f in flights])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无航班数据")
