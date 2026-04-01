"""行程方案视图 — 逐日行程 + 预算 + 方案对比 + 导出"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from core.trip_generator import generate_trip
from exporters.markdown_exporter import export_trip_markdown


def render_trip_tab(
    origin: str, destination: str, start_date: str, end_date: str,
    budget: int = 8000, hotel_type: str = None,
    course_names: list[str] = None,
):
    """渲染行程方案 Tab"""

    st.header("📅 行程方案")

    with st.spinner("正在生成行程方案..."):
        trip = generate_trip(
            origin, destination, start_date, end_date,
            budget, hotel_type, course_names,
        )

    # ─── 概览 ───
    summary = trip["summary"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("行程", summary["dates"])
    col2.metric("天数", f"{summary['nights']}晚")
    col3.metric("球场", f"{summary['courses_count']}个")

    total = summary["total_budget"]
    diff = budget - total
    col4.metric("预估总费用", f"¥{total}",
                delta=f"{'剩余' if diff >= 0 else '超出'}¥{abs(diff)}",
                delta_color="normal" if diff >= 0 else "inverse")

    # ─── 推荐航班+酒店 ───
    st.markdown("---")
    col_flight, col_hotel = st.columns(2)

    with col_flight:
        st.subheader("✈️ 推荐航班")
        if trip["outbound_flight"]:
            f = trip["outbound_flight"]
            st.markdown(f"**去程:** {f.get('airline', '')} {f.get('flight_no', '')}")
            st.markdown(f"🕐 {f['dep_time']} → {f['arr_time']}  |  💰 ¥{f['price']}")
        if trip["return_flight"]:
            f = trip["return_flight"]
            st.markdown(f"**返程:** {f.get('airline', '')} {f.get('flight_no', '')}")
            st.markdown(f"🕐 {f['dep_time']} → {f['arr_time']}  |  💰 ¥{f['price']}")

    with col_hotel:
        st.subheader("🏨 推荐酒店")
        if trip["hotel"]:
            h = trip["hotel"]
            st.markdown(f"**{h['name']}** ({h['type']})")
            st.markdown(f"💰 ¥{h['price_per_night']}/晚  |  ⭐ {h['rating']}")
            if h.get("distance_to_course_km"):
                st.markdown(f"📍 距球场 {h['distance_to_course_km']}km ({h.get('drive_minutes', '?')}分钟)")

    # ─── 逐日行程 ───
    st.markdown("---")
    st.subheader("📋 逐日行程")

    for day in trip["daily_plan"]:
        with st.expander(f"**{day['day_label']}** — {day['date']}", expanded=True):
            for activity in day["activities"]:
                st.markdown(f"- {activity}")

            if day.get("tips"):
                st.markdown("")
                for tip in day["tips"]:
                    st.caption(f"💡 {tip}")

    # ─── 预算明细 ───
    st.markdown("---")
    st.subheader("💰 预算明细")
    breakdown = trip["budget_breakdown"]

    col_chart, col_detail = st.columns([1, 1])

    with col_chart:
        labels = [k for k in breakdown if k != "合计"]
        values = [breakdown[k] for k in labels]
        colors = ["#2E86AB", "#A23B72", "#27AE60", "#F18F01"]

        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.4, marker_colors=colors,
            textinfo="label+percent",
            textposition="outside",
        ))
        fig.update_layout(
            height=350, margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            annotations=[dict(text=f"¥{breakdown['合计']}", x=0.5, y=0.5,
                              font_size=18, showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_detail:
        for item, cost in breakdown.items():
            if item == "合计":
                st.markdown(f"### 合计: ¥{cost}")
            else:
                pct = round(cost / breakdown["合计"] * 100) if breakdown["合计"] else 0
                bar_width = pct * 2
                st.markdown(f"**{item}** — ¥{cost} ({pct}%)")
                st.progress(pct / 100)

        if budget:
            if diff >= 0:
                st.success(f"预算还剩 ¥{diff}")
            else:
                st.error(f"超出预算 ¥{abs(diff)}，建议选择经济版方案")

    # ─── 三档方案对比 ───
    st.markdown("---")
    st.subheader("🔄 方案对比")
    tiers = trip["tiers"]

    cols = st.columns(3)
    for i, (tier_name, tier) in enumerate(tiers.items()):
        with cols[i]:
            emoji = {"经济": "💚", "舒适": "💙", "豪华": "❤️"}.get(tier_name, "⚪")
            is_recommended = (tier_name == "舒适")

            if is_recommended:
                st.markdown(f"### {emoji} {tier_name}版 ⭐推荐")
            else:
                st.markdown(f"### {emoji} {tier_name}版")

            st.markdown(f"**总计: ¥{tier['total']}**")

            tier_diff = budget - tier["total"]
            if tier_diff >= 0:
                st.caption(f"预算内，剩余 ¥{tier_diff}")
            else:
                st.caption(f"超出预算 ¥{abs(tier_diff)}")

            st.markdown("---")
            st.caption(f"✈️ 机票 ¥{tier['flight_cost']}")
            st.caption(f"🏨 酒店 ¥{tier['hotel_cost']}")
            st.caption(f"⛳ 果岭费 ¥{tier['green_fee']}")
            st.caption(f"🍽️ 餐饮交通 ¥{tier['misc']}")

            if tier["hotel"]:
                st.info(f"🏨 {tier['hotel']['name']}")
            if tier["flight"]:
                st.info(f"✈️ {tier['flight'].get('airline', '')} ¥{tier['flight']['price']}")

    # ─── 相关优惠 ───
    if trip["coupons"]:
        st.markdown("---")
        st.subheader("🏷️ 相关优惠")
        for c in trip["coupons"]:
            col_c1, col_c2 = st.columns([4, 1])
            with col_c1:
                st.markdown(f"**{c['title']}** — {c.get('description', '')}")
                st.caption(f"来源: {c['source']}")
            with col_c2:
                st.success(f"省 ¥{c['savings']}")

    # ─── 导出 ───
    st.markdown("---")
    st.subheader("📤 导出行程")

    col_md, col_notion = st.columns(2)
    with col_md:
        md_content = export_trip_markdown(trip)
        st.download_button(
            "📄 下载 Markdown",
            data=md_content,
            file_name=f"行程_{summary['destination']}_{start_date}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_notion:
        st.button(
            "📤 导出到 Notion",
            use_container_width=True,
            disabled=True,
            help="Notion 导出功能即将上线",
        )
