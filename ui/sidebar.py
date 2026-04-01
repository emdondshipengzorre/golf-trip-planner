"""参数面板"""

import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).parent.parent / "data"


def load_cities():
    with open(DATA_DIR / "cities.json", "r", encoding="utf-8") as f:
        return json.load(f)["cities"]


def load_courses():
    with open(DATA_DIR / "golf_courses.json", "r", encoding="utf-8") as f:
        return json.load(f)["courses"]


def render_sidebar() -> dict:
    """渲染侧边栏参数面板，返回用户选择的参数"""
    cities = load_cities()
    courses = load_courses()
    city_names = [c["name"] for c in cities]

    st.sidebar.markdown("""
    <div style="text-align:center; padding:0.5rem 0 0.8rem 0">
        <span style="font-size:2.5rem">⛳</span>
        <h2 style="margin:0.2rem 0 0 0; font-size:1.3rem">旅行规划器</h2>
        <p style="margin:0; font-size:0.75rem; opacity:0.7">Golf Trip Planner</p>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # ── 航线 ──
    st.sidebar.markdown("##### ✈️ 航线")
    origin_idx = city_names.index("北京") if "北京" in city_names else 0
    origin = st.sidebar.selectbox("出发城市", city_names, index=origin_idx)

    dest_options = [c for c in city_names if c != origin]
    destination = st.sidebar.selectbox("目的地", dest_options)

    st.sidebar.markdown("---")

    # ── 日期 ──
    st.sidebar.markdown("##### 📅 出行日期")
    today = date.today()
    default_start = today + timedelta(days=30)
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("出发", default_start)
    end_date = col2.date_input("返回", default_start + timedelta(days=4))

    if end_date <= start_date:
        st.sidebar.error("返回日期必须晚于出发日期")
        end_date = start_date + timedelta(days=1)

    nights = (end_date - start_date).days
    st.sidebar.caption(f"共 {nights} 晚 {nights + 1} 天")

    st.sidebar.markdown("---")

    # ── 预算 ──
    st.sidebar.markdown("##### 💰 预算")
    budget = st.sidebar.slider(
        "总预算 (¥)", min_value=3000, max_value=20000,
        value=8000, step=500, format="¥%d",
    )

    # ── 住宿 ──
    st.sidebar.markdown("##### 🏨 住宿偏好")
    hotel_pref = st.sidebar.radio(
        "住宿类型", ["不限", "经济", "舒适", "豪华"], horizontal=True,
        label_visibility="collapsed",
    )
    hotel_type = None if hotel_pref == "不限" else hotel_pref

    st.sidebar.markdown("---")

    # ── 球场 ──
    st.sidebar.markdown("##### ⛳ 球场选择")
    dest_courses = [c for c in courses if c["city"] == destination]
    course_names = [c["name"] for c in dest_courses]

    if course_names:
        selected_courses = st.sidebar.multiselect(
            "选择球场", course_names,
            default=course_names[:2],
            label_visibility="collapsed",
        )
        # 球场简要信息
        for c in dest_courses:
            if c["name"] in selected_courses:
                fee = f"¥{c['green_fee_range'][0]}~{c['green_fee_range'][1]}"
                st.sidebar.caption(f"  {c['name']} — {fee}")
    else:
        selected_courses = []
        st.sidebar.caption(f"暂无{destination}的球场数据")

    st.sidebar.markdown("---")

    # ── 高级选项 ──
    with st.sidebar.expander("⚙️ 高级选项"):
        trend_days = st.slider("价格趋势查看天数", 7, 60, 30)

    # ── 生成按钮 ──
    st.sidebar.markdown("")
    generate = st.sidebar.button("🔍 生成方案", type="primary", use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("数据仅供参考，实际价格以购买时为准")

    return {
        "origin": origin,
        "destination": destination,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "budget": budget,
        "hotel_type": hotel_type,
        "selected_courses": selected_courses,
        "trend_days": trend_days,
        "generate": generate,
    }
