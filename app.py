"""⛳ 高尔夫旅行规划器 — Streamlit 主入口"""
from __future__ import annotations

import logging
import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

st.set_page_config(
    page_title="高尔夫旅行规划器",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded",
)

import json
from pathlib import Path

from ui.styles import inject_styles, render_header, render_footer
from ui.sidebar import render_sidebar
from ui.flight_view import render_flight_tab
from ui.hotel_view import render_hotel_tab
from ui.coupon_view import render_coupon_tab
from ui.map_view import render_map_tab
from ui.trip_view import render_trip_tab
from ui.weather_view import render_weather_tab

DATA_DIR = Path(__file__).parent / "data"


def load_courses():
    with open(DATA_DIR / "golf_courses.json", "r", encoding="utf-8") as f:
        return json.load(f)["courses"]


def _check_api_keys():
    """检查 API 密钥配置状态"""
    from scrapers.base import get_api_key
    keys = {
        "AMADEUS_API_KEY": get_api_key("AMADEUS_API_KEY"),
        "AMADEUS_API_SECRET": get_api_key("AMADEUS_API_SECRET"),
        "OPENWEATHER_API_KEY": get_api_key("OPENWEATHER_API_KEY"),
    }
    missing = [k for k, v in keys.items() if not v]
    return missing


def main():
    inject_styles()
    render_header()

    # API 密钥检查
    missing_keys = _check_api_keys()
    if missing_keys:
        with st.expander("⚠️ API 密钥未配置 — 点击查看设置指南", expanded=False):
            st.markdown("""
            本应用使用以下免费 API 获取实时数据：

            **1. Amadeus (机票 + 酒店)**
            - 访问 [developers.amadeus.com](https://developers.amadeus.com)
            - 注册 → 创建应用 → 获取 API Key 和 Secret
            - 免费额度：每月 2000 次请求

            **2. OpenWeatherMap (天气)**
            - 访问 [openweathermap.org](https://openweathermap.org/api)
            - 注册 → 获取 API Key
            - 免费额度：每天 1000 次请求

            **配置方法：** 在项目目录创建 `.streamlit/secrets.toml`：
            ```toml
            AMADEUS_API_KEY = "your_key_here"
            AMADEUS_API_SECRET = "your_secret_here"
            OPENWEATHER_API_KEY = "your_key_here"
            ```
            """)
            st.warning(f"未配置: {', '.join(missing_keys)}")

    # 侧边栏参数
    params = render_sidebar()

    # 获取目的地球场坐标
    courses = load_courses()
    dest_courses = [c for c in courses if c["city"] == params["destination"]]
    course_lat = dest_courses[0]["lat"] if dest_courses else None
    course_lng = dest_courses[0]["lng"] if dest_courses else None

    # Tab 布局
    tab_flight, tab_hotel, tab_weather, tab_coupon, tab_map, tab_trip = st.tabs([
        "✈️ 机票比价",
        "🏨 酒店推荐",
        "🌤️ 天气",
        "🏷️ 优惠信息",
        "🗺️ 地图",
        "📅 行程方案",
    ])

    with tab_flight:
        render_flight_tab(
            params["origin"], params["destination"],
            params["start_date"], params["trend_days"],
        )

    with tab_hotel:
        render_hotel_tab(
            params["destination"], params["start_date"], params["end_date"],
            course_lat, course_lng,
            budget_max=params["budget"],
            hotel_type=params["hotel_type"],
        )

    with tab_weather:
        render_weather_tab(params["destination"])

    with tab_coupon:
        course_name = params["selected_courses"][0] if params["selected_courses"] else None
        render_coupon_tab(params["destination"], course_name)

    with tab_map:
        render_map_tab(
            params["destination"], params["start_date"], params["end_date"],
            params["selected_courses"],
        )

    with tab_trip:
        if params["generate"]:
            render_trip_tab(
                params["origin"], params["destination"],
                params["start_date"], params["end_date"],
                params["budget"], params["hotel_type"],
                params["selected_courses"],
            )
        else:
            st.markdown("""
            <div style="text-align:center; padding:3rem 0; color:#888">
                <p style="font-size:3rem; margin-bottom:0.5rem">⛳</p>
                <p style="font-size:1.1rem">调整左侧参数后，点击「生成方案」</p>
                <p style="font-size:0.85rem">选择出发城市、目的地、日期和预算，一键生成完整旅行方案</p>
            </div>
            """, unsafe_allow_html=True)

    render_footer()


if __name__ == "__main__":
    main()
