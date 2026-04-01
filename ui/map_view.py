"""地图视图 — 球场 + 酒店标注 + 距离圈 + 路线"""
from __future__ import annotations

import json
from pathlib import Path

import folium
from folium import plugins
import streamlit as st
from streamlit_folium import st_folium

from scrapers.hotel_scraper import search_hotels

DATA_DIR = Path(__file__).parent.parent / "data"


def render_map_tab(
    city: str, checkin: str, checkout: str,
    selected_course_names: list[str] = None,
):
    """渲染地图 Tab"""

    st.header("🗺️ 球场 & 酒店地图")

    # 加载球场
    with open(DATA_DIR / "golf_courses.json", "r", encoding="utf-8") as f:
        all_courses = json.load(f)["courses"]
    city_courses = [c for c in all_courses if c["city"] == city]

    if not city_courses:
        st.info(f"暂无{city}的球场数据")
        return

    # 地图控制
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    with col_ctrl1:
        show_distance_circle = st.checkbox("显示距离圈 (5km/10km)", value=True)
    with col_ctrl2:
        show_route_lines = st.checkbox("显示酒店→球场连线", value=True)
    with col_ctrl3:
        hotel_filter = st.selectbox("酒店筛选", ["全部", "豪华", "舒适", "经济"])

    # 中心点
    selected_courses = [c for c in city_courses if selected_course_names and c["name"] in selected_course_names]
    if selected_courses:
        center_lat = sum(c["lat"] for c in selected_courses) / len(selected_courses)
        center_lng = sum(c["lng"] for c in selected_courses) / len(selected_courses)
    else:
        center_lat = sum(c["lat"] for c in city_courses) / len(city_courses)
        center_lng = sum(c["lng"] for c in city_courses) / len(city_courses)

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles="CartoDB positron")

    # 图层分组
    course_group = folium.FeatureGroup(name="⛳ 球场")
    hotel_group = folium.FeatureGroup(name="🏨 酒店")
    line_group = folium.FeatureGroup(name="📏 连线")

    # ─── 标注球场 ───
    for course in city_courses:
        is_selected = selected_course_names and course["name"] in selected_course_names
        color = "green" if is_selected else "lightgray"

        fee_low, fee_high = course["green_fee_range"]
        difficulty = "⭐" * course.get("difficulty", 3)
        scenery = "🌟" * course.get("scenery", 3)
        newbie = "✅ 新手友好" if course.get("newbie_friendly", 3) >= 4 else ""
        tags = " ".join(f'<span style="background:#e8f5e9;padding:1px 4px;border-radius:3px;font-size:11px">{t}</span>' for t in course.get("tags", []))

        popup_html = f"""
        <div style="width:220px;font-family:sans-serif">
            <h4 style="margin:0 0 6px 0;color:#2e7d32">⛳ {course['name']}</h4>
            <table style="font-size:12px;line-height:1.6">
                <tr><td>💰 果岭费</td><td>¥{fee_low}~¥{fee_high}</td></tr>
                <tr><td>📐 难度</td><td>{difficulty}</td></tr>
                <tr><td>🏞️ 风景</td><td>{scenery}</td></tr>
                <tr><td>✏️ 设计师</td><td>{course.get('designer', '未知')}</td></tr>
            </table>
            <div style="margin-top:4px">{tags}</div>
            {f'<div style="margin-top:4px;color:#4caf50;font-weight:bold">{newbie}</div>' if newbie else ''}
        </div>
        """

        folium.Marker(
            [course["lat"], course["lng"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"⛳ {course['name']} ¥{fee_low}~{fee_high}",
            icon=folium.Icon(color=color, icon="flag", prefix="glyphicon"),
        ).add_to(course_group)

        # 距离圈
        if is_selected and show_distance_circle:
            folium.Circle(
                [course["lat"], course["lng"]],
                radius=5000, color="#4caf50", fill=True,
                fill_opacity=0.05, weight=1, dash_array="5",
                tooltip="5km 范围",
            ).add_to(course_group)
            folium.Circle(
                [course["lat"], course["lng"]],
                radius=10000, color="#ff9800", fill=True,
                fill_opacity=0.03, weight=1, dash_array="5",
                tooltip="10km 范围",
            ).add_to(course_group)

    # ─── 标注酒店 ───
    course_lat = city_courses[0]["lat"]
    course_lng = city_courses[0]["lng"]
    hotels = search_hotels(city, checkin, checkout, course_lat, course_lng)

    if hotel_filter != "全部":
        hotels = [h for h in hotels if h["type"] == hotel_filter]

    type_colors = {"豪华": "red", "舒适": "blue", "经济": "orange"}
    type_icons = {"豪华": "star", "舒适": "home", "经济": "usd"}

    for hotel in hotels:
        if not hotel["lat"] or not hotel["lng"]:
            continue

        color = type_colors.get(hotel["type"], "blue")
        icon = type_icons.get(hotel["type"], "home")
        dist_text = f"{hotel['distance_to_course_km']}km" if hotel.get("distance_to_course_km") else "?"
        drive_text = f"{hotel['drive_minutes']}分钟" if hotel.get("drive_minutes") else "?"

        popup_html = f"""
        <div style="width:200px;font-family:sans-serif">
            <h4 style="margin:0 0 6px 0;color:#1565c0">🏨 {hotel['name']}</h4>
            <table style="font-size:12px;line-height:1.6">
                <tr><td>类型</td><td>{hotel['type']}</td></tr>
                <tr><td>💰 价格</td><td><b>¥{hotel['price_per_night']}/晚</b></td></tr>
                <tr><td>⭐ 评分</td><td>{hotel['rating']}</td></tr>
                <tr><td>📍 距球场</td><td>{dist_text}</td></tr>
                <tr><td>🚗 车程</td><td>{drive_text}</td></tr>
                <tr><td>💎 性价比</td><td>{hotel['value_score']}</td></tr>
            </table>
            <div style="margin-top:4px;font-size:11px;color:#888">来源: {hotel.get('source', '—')}</div>
        </div>
        """

        folium.Marker(
            [hotel["lat"], hotel["lng"]],
            popup=folium.Popup(popup_html, max_width=230),
            tooltip=f"🏨 {hotel['name']} ¥{hotel['price_per_night']}",
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(hotel_group)

        # 酒店→球场连线
        if show_route_lines and selected_courses:
            nearest_course = min(selected_courses,
                                  key=lambda c: (c["lat"] - hotel["lat"])**2 + (c["lng"] - hotel["lng"])**2)
            folium.PolyLine(
                [[hotel["lat"], hotel["lng"]], [nearest_course["lat"], nearest_course["lng"]]],
                color=color, weight=1.5, opacity=0.5, dash_array="4",
                tooltip=f"{hotel['name']} → {nearest_course['name']} {dist_text}",
            ).add_to(line_group)

    # 添加图层
    course_group.add_to(m)
    hotel_group.add_to(m)
    line_group.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # 图例
    st.markdown(
        "🟢 已选球场 | ⚪ 其他球场 | "
        "🔴 豪华酒店 | 🔵 舒适酒店 | 🟠 经济酒店 | "
        "🟢 5km圈 | 🟠 10km圈"
    )

    st_folium(m, width=None, height=550)

    # 地图下方统计
    if hotels:
        st.markdown("---")
        st.subheader("📊 酒店分布统计")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("酒店总数", len(hotels))
        types = {}
        for h in hotels:
            types[h["type"]] = types.get(h["type"], 0) + 1
        col2.metric("豪华", f"{types.get('豪华', 0)} 家")
        col3.metric("舒适", f"{types.get('舒适', 0)} 家")
        col4.metric("经济", f"{types.get('经济', 0)} 家")

        within_5km = [h for h in hotels if h.get("distance_to_course_km") and h["distance_to_course_km"] <= 5]
        within_10km = [h for h in hotels if h.get("distance_to_course_km") and h["distance_to_course_km"] <= 10]
        if within_5km or within_10km:
            col5, col6 = st.columns(2)
            col5.metric("5km 内酒店", f"{len(within_5km)} 家")
            col6.metric("10km 内酒店", f"{len(within_10km)} 家")
